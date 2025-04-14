import logging

from langgraph.graph import StateGraph, START

from arklex.env.workers.worker import BaseWorker, register_worker
from arklex.utils.graph_state import MessageState, StatusEnum
from arklex.env.workers.utils.chat_client import ChatClient

from arklex.orchestrator.NLU.nlu import SlotFilling

logger = logging.getLogger(__name__)
# @register_worker
class HITLWorker(BaseWorker):  
    description = "This is a template for a HITL worker."
    mode = None
    params = None
    verifier = []
    
    slot_fill_api: SlotFilling = None
    
    # def __init__(self, server_ip: str, server_port: int, name: str):
    def __init__(self, **kwargs):
        super().__init__()
                
        self.action_graph = self._create_action_graph()

    def verify_literal(self, state: MessageState) -> tuple[bool, str]:
        """Override this method to allow verification on the message, either orchestrator's message or user's message
        Case: user's message
        Before the bot generate the response for the user's query, the framework decide whether it need to call human for the help because the user directly request so
        Case: orchestrator's message
        After the bot generate the response for the user's query, the framework decide whether it need to call human for the help because of the low confidence of the bot's response

        Args:
            message (str): _description_

        Returns:
            tuple[bool, str]: _description_
        """
        return True, ""
    
    def verify_slots(self, message) -> tuple[bool, str]:
        ''' Override this method to allow verification on the slots'''
        return True, ""
    
    def verify(self, state: MessageState) -> tuple[bool, str]:
        ''' Override this method to allow advanced verification on MessageState object'''
        need_hitl, message_literal = self.verify_literal(state)
        if need_hitl:
            return True, message_literal
        
        need_hitl, message_slot = self.verify_slots(state['slots'])
        if need_hitl:
            return True, message_slot
        
        return False, ""
    
    def init_slotfilling(self, slotsfillapi):
        self.slotfillapi = SlotFilling(slotsfillapi)
        
    def create_prompt(self):
        ''' Create a prompt for the HITL mc worker '''
        return self.params['intro'] + '\n' + '\n'.join(f"({key}) {item}" for key, item in self.params['choices'].items())
            
    def chat(self, state: MessageState) -> MessageState:
        ''' Connects to chat with the human in the loop '''
        client = ChatClient(self.server_ip, self.server_port, name=self.name, mode='c')
        return client.sync_main()
        
        # arklex pseudocode
        # chat_history = await server_chat() # BACKEND CHATS WITH USER HERE'''
        # state['messageFlow'] = to_message_flow(chat_history)
        # messageFlow['result'] = chat_history[-1]
        return state
    
    def multiple_choice(self, state: MessageState) -> MessageState:
        ''' Connects to give human in the loop multiple choice'''
        client = ChatClient(self.server_ip, self.server_port, name=self.name, mode='ro')
        return client.sync_main(message=self.create_prompt())
    
    def hitl(self, state: MessageState) -> str:
        ''' Human in the loop function '''
        result = None
        match self.mode:
            case "chat":
                chat_result = self.chat(state)
                state['user_message'].history += ('\n' + chat_result)
                state['user_message'].message = chat_result.split(f'{self.name}: ')[-1].split(':')[0]
                result = "Live Chat Completed"

            case "mc":
                attempts = self.params["max_retries"]
                
                for _ in range(attempts):
                    selection = self.multiple_choice(state)

                    result = self.params["choices"].get(selection)
                        
                    if result:
                        break
                else:
                    result = self.params['default']
            
            case _:
                return self.error(state)
                
        state['response'] = result
        return state
        
    def fallback(self, state: MessageState) -> MessageState:
        """The message of the fallback

        Args:
            state (MessageState): _description_

        Returns:
            : 
        """
        state['message_flow'] = "The user don't need human help"
        state['status'] = StatusEnum.COMPLETE.value
        return state
            
    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("hitl", self.hitl)
        # Add edges
        workflow.add_edge(START, "hitl")
        return workflow
        
    def execute(self, state: MessageState) -> MessageState:
        if not self.verify(state):
            return self.error(state)
        
        graph = self.action_graph.compile()
        result = graph.invoke(state)
        return result
    
@register_worker
class HITLWorkerTestChat(HITLWorker):
    """This worker is designed to start live chat locally
    Status: Not in use (as of 2025-02-20)

    Args:
        HITLWorker (_type_): _description_

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """

    description = "Chat with a real end user"
    mode = "chat"
    
    def __init__(self, **kwargs):
        super().__init__()
        self.server_ip = kwargs.get('server_ip')
        self.server_port = kwargs.get('server_port')
        self.name = kwargs.get('name')
        
        if not self.server_ip or not self.server_port:
            raise ValueError("Server IP and Port are required")
    
    def verify_literal(self, message: str) -> bool:
        return "chat" in message
    
@register_worker
class HITLWorkerTestMC(HITLWorker):
    """This worker is designed to start multiple choice human-in-the-loop worker locally
    Status: Not in use (as of 2025-02-20)

    Args:
        HITLWorker (_type_): _description_

    Returns:
        _type_: _description_
    """

    description = "Get confirmation from a real end user in purchasing"
    mode = "mc"
    params = {
        "intro": "Should the user continue with this purchase? (Y/N)",
        "max_retries": 5,
        'default': 'User is not allowed to continue with the purchase',
        "choices": {
            "Y": "User is allowed to continue with the purchase",
            "N": "User is not allowed to continue with the purchase"
        }
    }
    
    def __init__(self, **kwargs):
        super().__init__()
        self.server_ip = kwargs.get('server_ip')
        self.server_port = kwargs.get('server_port')
        self.name = kwargs.get('name')
    
    def verify_literal(self, message: str) -> bool:
        return "buy" in message
    
@register_worker
class HITLWorkerChatFlag(HITLWorker):
    """This worker is designed to start live chat with another built server. 
    So it will return the indicator of what type of human help needed.

    Args:
        HITLWorker (_type_): _description_

    Returns:
        MessageState: with hitl value in the MessageState[metadata]
    """
    description = "Human in the loop worker"
    mode = "chat"
    
    def verify_literal(self, state: MessageState) -> bool:
        """[TODO] Need to implement for orchestrator message as well
        (as of 2025-02-20)
        This method is to check the message from the user, since in the NLU, we already determine that the user wants to chat with the human in the loop.

        Args:
            message (str): _description_

        Returns:
            bool: _description_
        """
        message = "I'll connect you to a representative!"

        return True, message
    
    def execute(self, state: MessageState) -> MessageState:
        if not state['metadata'].get('hitl'):
            need_hitl, message = self.verify(state)
            if not need_hitl:
                return self.fallback(state)
            
            state["message_flow"] = message
            state['metadata']['hitl'] = 'live'
            state['status'] = StatusEnum.STAY.value
        
        else:
            state['message_flow'] = 'Live chat completed'
            state['metadata']['hitl'] = None
            state['status'] = StatusEnum.COMPLETE.value
        
        logger.info(state['message_flow'])
        return state
    
@register_worker
class HITLWorkerMCFlag(HITLWorker):
    """This worker is designed to start live chat with another built server. 
    So it will return the indicator of what type of human help needed.
    Status: Not in use (as of 2025-02-20)

    Args:
        HITLWorker (_type_): _description_

    Returns:
        MessageState: with hitl value in the MessageState[metadata]
    """

    description = "Get confirmation from a real end user in purchasing"
    mode = "mc"
    params = {
        "intro": "Should the user continue with this purchase? (Y/N)",
        "max_retries": 5,
        'default': 'User is not allowed to continue with the purchase',
        "choices": {
            "Y": "User is allowed to continue with the purchase",
            "N": "User is not allowed to continue with the purchase"
        }
    }
    
    def verify_literal(self, message: str) -> bool:
        return "buy" in message
    
    def execute(self, state: MessageState) -> MessageState:
        if not state['metadata'].get('hitl'):
            need_hitl, _ = self.verify(state)
            if not need_hitl:
                return self.fallback(state)
            
            state['response'] = '[[sending confirmation : this should not show up for user]]'
            state['metadata']['hitl'] = 'mc'
            state['metadata]']['attempts'] = self.params.get("max_retries", 3)
            state['status'] = StatusEnum.STAY.value
        
        else:
            result = self.params["choices"].get(state.user_message.message) # not actually user message but system confirmation
            
            if result:
                state['response'] = result
                state['metadata']['hitl'] = None
                state['status'] = StatusEnum.COMPLETE.value
                return state
            
            state['metadata]']['attempts'] -= 1
            if state['metadata]']['attempts'] <= 0:
                state['response'] = self.params['default']
                state['metadata']['hitl'] = None
                state['status'] = StatusEnum.INCOMPLETE.value
                return state
                    
            state['response'] = '[[sending confirmation : this should not show up for user]]'
            state['metadata']['hitl'] = 'mc'
            state['status'] = StatusEnum.STAY.value
            
        return state