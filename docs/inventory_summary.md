# LLM Calls Inventory — Summary

Total call sites: **31**

## By classification

- unknown: 25
- infra: 5
- agent: 1

## By task_type

- TaskType.PLANNING: 7
- Constant(value=None): 6
- TaskType.REASONING: 4
- reasoning: 4
- unknown: 4
- Name(id='task_type', ctx=Load()): 2
- IfExp(test=UnaryOp(op=Not(), operand=Name(id='task_type', ctx=Load())), body=Attribute(value=Name(id='TaskType', ctx=Load()), attr='DEFAULT', ctx=Load()), orelse=Call(func=Name(id='TaskType', ctx=Load()), args=[Name(id='task_type', ctx=Load())], keywords=[])): 1
- Name(id='ollama_task_type', ctx=Load()): 1
- TaskType.CODE_GENERATION: 1
- code_generation: 1

## By has_system_prompt

- yes: 16
- no: 15

## By prompt_source

- inline: 29
- unknown: 2
