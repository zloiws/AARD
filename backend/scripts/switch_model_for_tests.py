"""
Script to switch to gemma3:4b model on Server 2 - Coding for testing
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from app.services.ollama_service import OllamaService
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


def switch_to_gemma3_for_tests():
    """Switch to gemma3:4b model on Server 2 - Coding for testing"""
    db: Session = SessionLocal()
    
    try:
        # Find Server 2 - Coding
        server = db.query(OllamaServer).filter(
            OllamaServer.name == "Server 2 - Coding"
        ).first()
        
        if not server:
            print("❌ Server 2 - Coding not found")
            print("Available servers:")
            servers = db.query(OllamaServer).all()
            for s in servers:
                print(f"  - {s.name} ({s.url})")
            return False
        
        print(f"✓ Found server: {server.name} ({server.url})")
        
        # Find gemma3:4b model
        model = db.query(OllamaModel).filter(
            OllamaModel.server_id == str(server.id),
            OllamaModel.model_name == "gemma3:4b"
        ).first()
        
        if not model:
            print(f"❌ Model gemma3:4b not found on {server.name}")
            print(f"Available models on {server.name}:")
            models = OllamaService.get_models_for_server(db, str(server.id))
            for m in models:
                print(f"  - {m.model_name} (active: {m.is_active})")
            
            # Offer to create the model
            print("\n💡 You can add the model manually via the API or web interface")
            return False
        
        print(f"✓ Found model: {model.model_name}")
        
        # Make it active and set as default for code generation
        model.is_active = True
        
        # Set capabilities for coding
        if not model.capabilities:
            model.capabilities = []
        if "code_generation" not in model.capabilities:
            model.capabilities.append("code_generation")
        if "code_analysis" not in model.capabilities:
            model.capabilities.append("code_analysis")
        if "code" not in model.capabilities:
            model.capabilities.append("code")
        
        # Set high priority for testing
        model.priority = 10
        
        db.commit()
        db.refresh(model)
        
        print(f"✓ Activated model: {model.model_name}")
        print(f"  - Capabilities: {model.capabilities}")
        print(f"  - Priority: {model.priority}")
        print(f"  - Active: {model.is_active}")
        
        print("\n✅ Model switched successfully!")
        print("   You can now use this model for testing.")
        print("   Note: Make sure to select 'Server 2 - Coding' and 'gemma3:4b' in the UI")
        
        return True
        
    except Exception as e:
        logger.error(f"Error switching model: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🔄 Switching to gemma3:4b on Server 2 - Coding for testing...\n")
    success = switch_to_gemma3_for_tests()
    sys.exit(0 if success else 1)

