# 📚 Purpose of `base.py`

## 🎯 Overview

`base.py` contains the **base classes** and **common functionality** for all agents in the RAG evaluation pipeline. It provides a foundation for consistent agent implementation across the system.

---

## 🏗️ Components

### **1. AgentState (Data Class)**

```python
@dataclass
class AgentState:
    """State object passed between agents."""
    session_id: str          # Unique session identifier
    data: Dict[str, Any]     # Actual data (documents, responses, etc.)
    metadata: Dict[str, Any] # Additional metadata (timestamps, configs, etc.)
    timestamp: float         # When the state was created
```

**Purpose:**
- Represents the state passed between agents in the pipeline
- Carries data from one agent to the next
- Maintains session context throughout execution

**Used by:**
- All agents to receive and return state
- LangGraph workflow to manage pipeline flow

---

### **2. BaseAgent (Abstract Base Class)**

```python
class BaseAgent(ABC, MetricsMixin, LoggerMixin):
    """Base class for all agents in the pipeline."""
```

**Purpose:**
- Abstract base class that all agents inherit from
- Provides common functionality for all agents
- Includes monitoring (MetricsMixin) and logging (LoggerMixin)

**Features:**
- Configuration management (`config`, `timeout`, `max_retries`)
- Session ID generation (`_create_session_id()`)
- State validation (`_validate_state()`)
- Metrics recording (`_record_execution_time()`, `_record_success()`, `_record_failure()`)

**Inherits from:**
- `MetricsMixin` - CloudWatch metrics recording
- `LoggerMixin` - Structured logging

**Abstract Method:**
```python
async def execute(self, state: AgentState) -> AgentState:
    """Execute the agent's main logic."""
    pass
```
All derived agents must implement this.

---

### **3. RetrievalAgent (Specialized Base Class)**

```python
class RetrievalAgent(BaseAgent):
    """Abstract base for retrieval agents."""
    def __init__(self, config: Dict[str, Any], **kwargs):
        super().__init__(config, **kwargs)
        self.batch_size = config.get('batch_size', 10)
```

**Purpose:**
- Specialized base class for retrieval-type agents
- Adds `batch_size` configuration
- Inherits from `BaseAgent`

**Used by:**
- `S3RetrievalAgent` (`agents/retrieval_agent.py`)

---

### **4. DevAgent (Specialized Base Class)**

```python
class DevAgent(BaseAgent):
    """Abstract base for development agents."""
    def __init__(self, config: Dict[str, Any], **kwargs):
        super().__init__(config, **kwargs)
        self.context_window = config.get('context_window', 8000)
```

**Purpose:**
- Specialized base class for development-type agents
- Adds `context_window` configuration for handling context size
- Inherits from `BaseAgent`

**Used by:**
- `DevAgent` in `agents/dev_agent.py` (Note: There's naming overlap here - the implementation class also called DevAgent extends this)

---

### **5. EvaluatorAgent (Specialized Base Class)**

```python
class EvaluatorAgent(BaseAgent):
    """Abstract base for evaluation agents."""
```

**Purpose:**
- Specialized base class for evaluation-type agents
- Inherits from `BaseAgent`
- Provides foundation for evaluator agents

**Used by:**
- `RAGEvaluatorAgent` (`agents/evaluator_agent.py`)

---

## 💡 How It Works in the Pipeline

### **Inheritance Hierarchy:**

```
BaseAgent (base.py)
    ├─ RetrievalAgent (base.py)
    │   └─ S3RetrievalAgent (retrieval_agent.py) ✅
    ├─ DevAgent (base.py)
    │   └─ DevAgent (dev_agent.py) ✅
    └─ EvaluatorAgent (base.py)
        └─ RAGEvaluatorAgent (evaluator_agent.py) ✅
```

### **Usage Pattern:**

```python
# In retrieval_agent.py
from .base import RetrievalAgent, AgentState

class S3RetrievalAgent(RetrievalAgent):
    async def execute(self, state: AgentState) -> AgentState:
        # Inherits all base functionality
        # Must implement execute() method
        # Can use helper methods like:
        # - _record_execution_time()
        # - _record_success()
        # - _record_failure()
        # - _validate_state()
        pass
```

---

## 🎯 Key Benefits

### **1. Code Reusability**
- Common functionality in one place
- No duplication across agents
- Consistent behavior

### **2. Monitoring & Observability**
- Built-in metrics recording
- Structured logging
- Execution time tracking
- Success/failure tracking

### **3. Consistency**
- All agents have same interface
- Same state structure
- Same error handling pattern

### **4. Extensibility**
- Easy to add new agents
- Inherit base functionality
- Override as needed

---

## 📊 Example: How an Agent Uses BaseAgent

```python
# In any agent implementation
from .base import BaseAgent, AgentState

class MyAgent(BaseAgent):
    async def execute(self, state: AgentState) -> AgentState:
        start_time = time.time()
        
        try:
            # Agent's main logic here
            state.data['result'] = "Some result"
            
            # Record metrics (from BaseAgent)
            duration = time.time() - start_time
            self._record_execution_time("my_operation", duration, state.session_id)
            self._record_success("my_operation", state.session_id)
            
            return state
            
        except Exception as e:
            # Record failure (from BaseAgent)
            self._record_failure("my_operation", state.session_id, e)
            raise
```

---

## 🔍 Common Methods Available to All Agents

### **State Management**
- `_create_session_id()` - Generate unique session IDs
- `_validate_state()` - Validate agent state

### **Metrics**
- `_record_execution_time()` - Record operation duration
- `_record_success()` - Record successful operations
- `_record_failure()` - Record failed operations

### **From MetricsMixin**
- `record_agent_metric()` - Custom metric recording
- CloudWatch integration

### **From LoggerMixin**
- `log_with_context()` - Structured logging
- Context-aware log messages

---

## ✅ Summary

**Purpose of base.py:**
1. 🏗️ Provides foundation classes for all agents
2. 📊 Ensures consistent monitoring and logging
3. 🔄 Manages state transitions between agents
4. 🎯 Implements common agent functionality
5. 📈 Records metrics and logs automatically

**What agents get from base.py:**
- ✅ Consistent state management
- ✅ Built-in monitoring and logging
- ✅ Metrics recording capabilities
- ✅ Error handling patterns
- ✅ Session management
- ✅ Configuration management

**Without base.py:**
- ❌ Code duplication across agents
- ❌ Inconsistent behavior
- ❌ No standard metrics/logging
- ❌ Hard to maintain

**With base.py:**
- ✅ Clean, maintainable code
- ✅ Consistent agent behavior
- ✅ Built-in observability
- ✅ Easy to add new agents

---

## 🎯 Key Takeaway

`base.py` is the **foundation** that ensures all agents in your RAG evaluation pipeline work consistently with proper monitoring, logging, and state management. It's essential for maintaining code quality and observability across your multi-agent system.

