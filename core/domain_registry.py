"""
Domain Registry — Part 2.3: Register all domain agents.
"""
from core.domain_agent import DomainRegistry, DomainConfig
from actions.computer_control import ComputerControlAgent
from actions.phone_comms import PhoneCommsAgent
from actions.smart_home import SmartHomeAgent
from actions.trading_orchestration import TradingOrchestrationAgent
from actions.opportunity_discovery import OpportunityDiscoveryAgent
from actions.content_engine import ContentEngineAgent
from actions.autonomous_worker import AutonomousWorker
from actions.money_makers import handle as money_makers_handle
from actions.gumroad_api import handle as gumroad_handle
from actions.stripe_payments import handle as stripe_handle
from actions.marketing_engine import handle as marketing_handle
from actions.namibian_payments import handle as namibian_payments_handle

def init_domain_registry() -> 'DomainRegistry':
    """Initialize and register all domain agents."""
    registry = DomainRegistry()
    
    # Register core domain agents
    registry.register(ComputerControlAgent())
    registry.register(PhoneCommsAgent())
    registry.register(SmartHomeAgent())
    registry.register(TradingOrchestrationAgent())
    registry.register(OpportunityDiscoveryAgent())
    registry.register(ContentEngineAgent())
    
    # Register existing functional agents
    registry.register(AutonomousWorker())
    
    return registry

_initialized_registry = None

def get_initialized_registry():
    """Get initialized registry singleton."""
    global _initialized_registry
    if _initialized_registry is None:
        _initialized_registry = init_domain_registry()
    return _initialized_registry

def get_domain(domain: str):
    """Get a domain agent by name."""
    return get_initialized_registry().get(domain)

def get_all_domains():
    return get_initialized_registry().get_all()

def get_all_status():
    return get_initialized_registry().get_all_status()

def get_all_proposals():
    return get_initialized_registry().get_all_proposals()