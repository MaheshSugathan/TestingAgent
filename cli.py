"""Command-line interface for the RAG evaluation pipeline."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from config import ConfigManager
from orchestration import RAGEvaluationPipeline
from observability import setup_logger, MetricsCollector


console = Console()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """RAG Evaluation Pipeline CLI."""
    ctx.ensure_object(dict)
    
    # Load configuration
    try:
        config_manager = ConfigManager(config)
        ctx.obj['config'] = config_manager.load_config()
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        sys.exit(1)
    
    # Setup logging
    log_level = "DEBUG" if verbose else ctx.obj['config'].get('logging', {}).get('level', 'INFO')
    logger = setup_logger(
        level=log_level,
        cloudwatch_log_group=ctx.obj['config'].get('aws', {}).get('cloudwatch', {}).get('log_group'),
        aws_region=ctx.obj['config'].get('aws', {}).get('region', 'us-east-1')
    )
    
    ctx.obj['logger'] = logger


@cli.command()
@click.option('--single-turn', is_flag=True, help='Run single-turn evaluation')
@click.option('--multi-turn', is_flag=True, help='Run multi-turn evaluation')
@click.option('--judge', type=click.Choice(['ragas', 'llm', 'both']), default='both', help='Evaluation method')
@click.option('--agentcore-url', help='AgentCore service URL')
@click.option('--bill-agent', help='Bill agent name')
@click.option('--query', '-q', help='Single query for evaluation')
@click.option('--queries-file', type=click.Path(exists=True), help='File containing queries (one per line)')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--session-id', help='Custom session ID')
@click.pass_context
def evaluate(ctx, single_turn, multi_turn, judge, agentcore_url, askbill_agent, query, queries_file, output, session_id):
    """Run RAG evaluation pipeline."""
    
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    # Determine evaluation type
    if single_turn and multi_turn:
        console.print("[red]Cannot specify both --single-turn and --multi-turn[/red]")
        sys.exit(1)
    elif not single_turn and not multi_turn:
        single_turn = True  # Default to single-turn
    
    # Get queries
    queries = []
    if query:
        queries = [query]
    elif queries_file:
        with open(queries_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
    else:
        # Default queries
        queries = [
            "What is the main topic of the document?",
            "Can you summarize the key points?",
            "What are the important details mentioned?"
        ]
    
    if not queries:
        console.print("[red]No queries provided[/red]")
        sys.exit(1)
    
    # Update configuration based on judge selection
    if judge == 'ragas':
        config['evaluation']['ragas']['enabled'] = True
        config['evaluation']['llm_judge']['enabled'] = False
    elif judge == 'llm':
        config['evaluation']['ragas']['enabled'] = False
        config['evaluation']['llm_judge']['enabled'] = True
    # 'both' is already configured in the default config
    
    # Update AgentCore configuration if provided
    if agentcore_url:
        config.setdefault('agentcore', {})['base_url'] = agentcore_url
    
    if askbill_agent:
        config.setdefault('agentcore', {}).setdefault('askbill', {})['agent_name'] = askbill_agent
    
    # Run evaluation
    asyncio.run(_run_evaluation(
        config=config,
        logger=logger,
        queries=queries,
        single_turn=single_turn,
        session_id=session_id,
        output_file=output
    ))


async def _run_evaluation(
    config: dict,
    logger,
    queries: List[str],
    single_turn: bool,
    session_id: Optional[str],
    output_file: Optional[str]
):
    """Run the evaluation pipeline."""
    
    try:
        # Initialize pipeline
        pipeline = RAGEvaluationPipeline(config, logger)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Running RAG evaluation pipeline...", total=None)
            
            if single_turn:
                # Run single-turn evaluation for each query
                results = []
                for i, query in enumerate(queries):
                    progress.update(task, description=f"Evaluating query {i+1}/{len(queries)}: {query[:50]}...")
                    
                    result = await pipeline.run_single_turn_evaluation(
                        query=query,
                        session_id=f"{session_id}-{i}" if session_id else None
                    )
                    results.append(result)
            else:
                # Run multi-turn evaluation
                progress.update(task, description="Running multi-turn evaluation...")
                result = await pipeline.run_multi_turn_evaluation(
                    queries=queries,
                    session_id=session_id
                )
                results = [result]
            
            progress.update(task, description="Pipeline completed!")
        
        # Display results
        _display_results(results, single_turn)
        
        # Save results if output file specified
        if output_file:
            _save_results(results, output_file)
            
    except Exception as e:
        console.print(f"[red]Pipeline execution failed: {e}[/red]")
        logger.error(f"Pipeline execution failed: {e}")
        sys.exit(1)


def _display_results(results: List, single_turn: bool):
    """Display evaluation results."""
    
    if single_turn and len(results) > 1:
        # Display summary table for multiple single-turn evaluations
        table = Table(title="Evaluation Summary")
        table.add_column("Query", style="cyan", width=50)
        table.add_column("Success", style="green")
        table.add_column("Execution Time", style="yellow")
        table.add_column("Overall Score", style="magenta")
        
        for result in results:
            summary = result.get_pipeline_summary()
            query = summary.get("agent_results", {}).get("dev", {}).get("metadata", {}).get("queries", [""])[0]
            
            table.add_row(
                query[:47] + "..." if len(query) > 50 else query,
                "✅" if summary["success"] else "❌",
                f"{summary['execution_time']:.2f}s",
                f"{_get_overall_score(result):.2f}"
            )
        
        console.print(table)
    else:
        # Display detailed results for single evaluation
        result = results[0]
        summary = result.get_pipeline_summary()
        
        # Display pipeline summary
        console.print(Panel.fit(
            f"Session ID: {summary['session_id']}\n"
            f"Execution Time: {summary['execution_time']:.2f}s\n"
            f"Success: {'✅' if summary['success'] else '❌'}\n"
            f"Overall Score: {_get_overall_score(result):.2f}",
            title="Pipeline Summary",
            border_style="green" if summary["success"] else "red"
        ))
        
        # Display evaluation details
        if summary["success"] and "evaluation_summary" in summary:
            eval_summary = summary["evaluation_summary"]
            
            console.print("\n[bold]Evaluation Results:[/bold]")
            
            for method, scores in eval_summary["average_scores"].items():
                console.print(f"\n[bold]{method.upper()}:[/bold]")
                for metric, score in scores.items():
                    console.print(f"  {metric}: {score:.3f}")


def _get_overall_score(result) -> float:
    """Get overall score from result."""
    try:
        evaluation_results = result.get_data("evaluator", "evaluation_results")
        if evaluation_results:
            # Calculate average score from first result
            first_result = evaluation_results[0]
            evaluations = first_result.get("evaluations", {})
            
            scores = []
            for method in ["ragas", "llm_judge"]:
                if method in evaluations and "metrics" in evaluations[method]:
                    metrics = evaluations[method]["metrics"]
                    method_scores = [v for v in metrics.values() if v is not None]
                    if method_scores:
                        scores.extend(method_scores)
            
            return sum(scores) / len(scores) if scores else 0.0
    except Exception:
        pass
    
    return 0.0


def _save_results(results: List, output_file: str):
    """Save results to file."""
    try:
        output_data = []
        for result in results:
            output_data.append(result.get_pipeline_summary())
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        console.print(f"[green]Results saved to {output_file}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to save results: {e}[/red]")


@cli.command()
@click.pass_context
def dashboard(ctx):
    """Create CloudWatch dashboard for monitoring."""
    from observability import CloudWatchHandler
    
    config = ctx.obj['config']
    
    try:
        handler = CloudWatchHandler(
            region=config.get('aws', {}).get('region', 'us-east-1')
        )
        
        dashboard_name = "RAG-Evaluation-Pipeline"
        metrics_config = config
        
        success = handler.create_dashboard(dashboard_name, metrics_config)
        
        if success:
            console.print(f"[green]Dashboard '{dashboard_name}' created successfully![/green]")
            console.print(f"[blue]View it in AWS CloudWatch console[/blue]")
        else:
            console.print(f"[red]Failed to create dashboard[/red]")
            
    except Exception as e:
        console.print(f"[red]Dashboard creation failed: {e}[/red]")


@cli.command()
@click.pass_context
def test(ctx):
    """Run basic connectivity tests."""
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    console.print("[bold]Running connectivity tests...[/bold]")
    
    # Test AWS credentials
    try:
        import boto3
        s3 = boto3.client('s3', region_name=config.get('aws', {}).get('region', 'us-east-1'))
        s3.list_buckets()
        console.print("✅ AWS credentials: OK")
    except Exception as e:
        console.print(f"❌ AWS credentials: {e}")
    
    # Test Bedrock access
    try:
        import boto3
        bedrock = boto3.client('bedrock-runtime', region_name=config.get('bedrock', {}).get('region', 'us-east-1'))
        bedrock.list_foundation_models()
        console.print("✅ Bedrock access: OK")
    except Exception as e:
        console.print(f"❌ Bedrock access: {e}")
    
    # Test S3 bucket access
    try:
        import boto3
        s3 = boto3.client('s3', region_name=config.get('aws', {}).get('region', 'us-east-1'))
        bucket_name = config.get('s3', {}).get('bucket', 'rag-evaluation-datasets')
        s3.head_bucket(Bucket=bucket_name)
        console.print("✅ S3 bucket access: OK")
    except Exception as e:
        console.print(f"❌ S3 bucket access: {e}")
    
    # Test AgentCore connectivity
    agentcore_config = config.get('agentcore', {})
    if agentcore_config.get('enabled', False):
        try:
            import requests
            base_url = agentcore_config.get('base_url', 'http://localhost:8000')
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                console.print("✅ AgentCore service: OK")
            else:
                console.print(f"❌ AgentCore service: HTTP {response.status_code}")
        except Exception as e:
            console.print(f"❌ AgentCore service: {e}")
        
        # Test Bill agent specifically
        try:
            bill_config = agentcore_config.get('bill', {})
            agent_name = bill_config.get('agent_name', 'bill')
            base_url = agentcore_config.get('base_url', 'http://localhost:8000')
            response = requests.get(f"{base_url}/agents/{agent_name}/health", timeout=5)
            if response.status_code == 200:
                console.print(f"✅ Bill agent ({agent_name}): OK")
            else:
                console.print(f"❌ Bill agent ({agent_name}): HTTP {response.status_code}")
        except Exception as e:
            console.print(f"❌ Bill agent: {e}")
    
    console.print("[bold]Connectivity tests completed![/bold]")


if __name__ == '__main__':
    cli()
