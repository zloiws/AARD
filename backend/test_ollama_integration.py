"""Test Ollama integration"""
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.core.ollama_client import get_ollama_client, TaskType


async def test_ollama():
    """Test Ollama client"""
    print("Testing Ollama Integration...\n")
    
    client = get_ollama_client()
    
    # List available models
    print("Available models:")
    for instance in client.instances:
        print(f"  - {instance.model}")
        print(f"    URL: {instance.url}")
        print(f"    Capabilities: {instance.capabilities}")
        print(f"    Max concurrent: {instance.max_concurrent}\n")
    
    # Test health checks
    print("Health checks:")
    for instance in client.instances:
        health = await client.health_check(instance)
        status = "✓ Healthy" if health else "✗ Unavailable"
        print(f"  {instance.model}: {status}")
    print()
    
    # Test model selection
    print("Model selection:")
    test_types = [
        TaskType.CODE_GENERATION,
        TaskType.REASONING,
        TaskType.GENERAL_CHAT,
    ]
    for task_type in test_types:
        instance = client.select_model_for_task(task_type)
        print(f"  {task_type.value}: {instance.model}")
    print()
    
    # Test simple generation (if instances are available)
    try:
        print("Testing generation (simple prompt)...")
        response = await client.generate(
            prompt="Say 'Hello, AARD!' in one sentence.",
            task_type=TaskType.GENERAL_CHAT
        )
        print(f"  ✓ Response received")
        print(f"  Model: {response.model}")
        print(f"  Response: {response.response[:100]}...")
        print(f"  Done: {response.done}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        print("  (This is OK if Ollama instances are not accessible)")
    
    await client.close()
    print("\n✓ Ollama client test complete!")


if __name__ == "__main__":
    asyncio.run(test_ollama())

