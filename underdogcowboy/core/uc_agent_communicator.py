"""
This module implements a communication bridge between the generic CLI library and the UC-specific agent system.

The pattern used here is a combination of the Adapter pattern and Dependency Injection, which allows for loose coupling
between the generic CLI library and the UC-specific agent implementation. This approach solves several key challenges:

1. Avoiding Circular Dependencies:
   By defining an abstract AgentCommunicator in the CLI library and implementing it in the UC library,
   we avoid circular imports between the two libraries.

2. Maintaining Separation of Concerns:
   The CLI library remains agnostic about the specific agent implementation, while the UC library
   can implement its own agent communication logic.

3. Enabling Flexibility and Extensibility:
   This pattern allows for easy swapping or updating of the agent communication implementation
   without modifying the core CLI library code.

How it works:

1. The CLI library defines an abstract AgentCommunicator class with a send_update method.
2. The GenericCLI class in the CLI library accepts an AgentCommunicator in its constructor.
3. This UCAgentCommunicator class implements the AgentCommunicator interface.
4. When initializing the CLI in the UC library, we create an instance of UCAgentCommunicator
   and pass it to the CLI constructor.
5. The CLI can now call send_update on its agent_communicator attribute, which will be
   routed to the UC-specific agent implementation.

This pattern allows the generic CLI library to communicate with the UC-specific agent
without directly depending on the UC library, maintaining a clean separation between
the two systems while still allowing them to interact.

The initial agent we using this for is: cliagent, so an otherlying llm (in cliagent)
can be used by the CLI library.


1. Adapter Pattern:
   The UCAgentCommunicator acts as an adapter between the generic AgentCommunicator
   interface (defined in the CLI library) and the UC-specific agent implementation.
   It translates the generic 'send_update' method into UC-specific agent communication.

   This pattern allows the CLI library to remain agnostic about the specific
   implementation of agent communication, while enabling UC to implement its
   own communication logic.

2. Dependency Injection:
   Instead of the CLI library creating or importing a specific agent communicator,
   it accepts any object that adheres to the AgentCommunicator interface.
   This UCAgentCommunicator is "injected" into the CLI at runtime.

   This pattern decouples the CLI library from UC-specific implementations,
   enhancing modularity and allowing for future extensions.

"""

from uccli import AgentCommunicator
import json
class UCAgentCommunicator(AgentCommunicator):
    def __init__(self, agent):
        self.agent = agent

    def send_update(self, update_data: dict):
        # Implement the actual communication with your Agent CLIBase here
        self.agent.receive_update(update_data)
        #print("Update to Agent CLIBase (UC test):")
        #print(json.dumps(update_data, indent=2))
