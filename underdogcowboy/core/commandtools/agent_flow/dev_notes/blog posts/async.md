

# Samenvatting 

Dit blogbericht beschrijft de ontwikkeling van een Text User Interface (TUI) voor Underdog Cowboy, een open-source platform onder de MIT-licentie dat het mogelijk maakt om de kracht van Language Models (LLMs) te benutten zonder uitgebreide programmeerkennis. Het doel van Underdog Cowboy is om individuen en teams te helpen hun ideeën om te zetten in functionele prototypes die door programmeurs kunnen worden verfijnd en opgeschaald.

Het belangrijkste technische vraagstuk dat hier wordt behandeld, is hoe meerdere achtergrondtaken met LLM-oproepen kunnen worden uitgevoerd zonder dat de TUI bevriest. Hiervoor wordt gebruikgemaakt van asyncio in combinatie met een ThreadPoolExecutor, waardoor zware LLM-bewerkingen asynchroon kunnen plaatsvinden en de interface responsief blijft.

Een ander belangrijk onderdeel is de integratie van LLM-oproepen in de event-gedreven architectuur van de TUI. Door gebruik te maken van events, zoals LLMCallComplete of LLMCallError, kunnen UI-componenten de resultaten van deze bewerkingen naadloos weergeven.

Toekomstige ontwikkelingen omvatten onder andere de integratie van Redis om multi-user functionaliteit mogelijk te maken, zodat meerdere gebruikers in real-time aan dezelfde workflows kunnen werken. Ook wordt gekeken naar het blijven uitvoeren van processen nadat de TUI is afgesloten, via een lokale of cloud-gebaseerde Redis-oplossing.

Met deze ontwikkelingen streeft Underdog Cowboy ernaar om AI-interacties toegankelijk en intuïtief te maken, zodat creatieve ideeën zich kunnen ontwikkelen en groeien.

# Bijgaande Instructie voor goede publicatie

- De blog post is in Markdown en heeft code blocks (zie beneden hoe dit in markdown gedaan wordt).
- De blog post heeft ook `dit soort` text.

- Draag zorg voor goede weergave van beide in the publieke blog post, de code blocks en de kleinere texts zoals `deze`.


## Start Blog Post

---

# Building a Responsive TUI: Leveraging Background LLM Calls Without Freezing the Interface

Underdog Cowboy, which is open source under the MIT License (a permissive license that allows for free use, modification, and distribution), is your bridge to harnessing the power of Language Models (LLMs) without needing extensive programming expertise. We designed it to help individuals and teams turn their ideas into functional prototypes that programmers can refine and scale.

To bridge the gap between the complex world of AI development and users with diverse technical abilities, we focus on creating simplified user experiences that empower individuals to harness the potential of AI and drive innovation forward. We enable seamless collaboration between non-technical innovators and developers, fostering a shared understanding that accelerates AI project development.

This philosophy has directly influenced the design and development of our Text User Interface (TUI) based on the Python Library `Textual`, which enhances the user experience for structured processes by enabling seamless interaction with a set of AI tools. One major technical challenge I've been tackling is how to run multiple background LLM calls from the TUI without freezing the interface, allowing users to continue working smoothly while these tasks are processed. This responsiveness is essential to maintain a fluid experience and ensure the interface remains interactive during background operations.

To overcome this challenge, I have employed a combination of asyncio and a ThreadPoolExecutor to decouple LLM calls from the UI. This allows the heavy lifting of LLM processing to occur asynchronously, ensuring that the main event loop remains responsive.

### Decoupling LLM Calls from the UI

To achieve this, I utilized `asyncio` in combination with a `ThreadPoolExecutor` to run LLM calls in the background. By offloading these tasks, the main TUI event loop remains responsive, allowing users to continue interacting with the interface. An asynchronous task queue (`asyncio.Queue`) is used to manage these calls, ensuring they are processed efficiently without risking concurrency issues.

### Event-Driven Integration

A key part of this solution is integrating the LLM calls into the event-driven architecture of the TUI. By leveraging a mixin (`MessageEmitterMixin`), the LLM manager emits events like `LLMCallComplete` or `LLMCallError` upon task completion or failure. These events are then picked up by UI components, ensuring results are reflected in the interface seamlessly.

For instance, consider the following integration within the AnalyzeUI class, which is a Textual `Widget`:

```python
@on(LLMCallComplete)
async def on_llm_call_complete(self, event: LLMCallComplete) -> None:
    if event.input_id == "analysis":
        self.update_and_show_result(event.result)
        self.query_one("#loading-indicator").add_class("hidden")

@on(LLMCallError)
async def on_llm_call_error(self, event: LLMCallError) -> None:
    if event.input_id == "analysis":
        self.show_error(event.error)
        self.query_one("#loading-indicator").add_class("hidden")
```

This ensures that once an LLM task is complete or fails, the UI is immediately updated to reflect the result, without the interface becoming unresponsive.

### Extensibility for LLM Functions

The architecture of this system is highly extensible. New LLM-related functions can be incorporated into  Widgets using the submit_llm_call() method. With a simple import, these functions can be reused across different parts of the TUI, making it easy to add or modify functionality. This method handles LLM function calls, including metadata like pre-prompts and post-prompts, and the functions are passed asynchronously, ensuring that the UI remains responsive throughout.

Here's an example of using submit_llm_call() to initiate an analysis:

```python
asyncio.create_task(self.llm_call_manager.submit_llm_call(
    llm_function=run_analysis,
    llm_config=llm_config,
    agent_name=current_agent,
    input_id="analysis",
    pre_prompt="Analyze this agent definition:",
    post_prompt=None
))
```

This call adds the task to an asynchronous queue, which the LLMCallManager then processes in the background, ensuring the TUI remains fully interactive.

### Handling Common Issues

During the development process, I've addressed several common challenges:

Thread Safety: Managing shared resources within `ThreadPoolExecutor` requires careful synchronization to prevent race conditions. Using an `asyncio.Queue` helps serialize tasks and maintain consistency.

State Consistency: Maintaining the UI state in sync with ongoing background tasks is critical. The event-driven approach ensures that changes from LLM processing are promptly reflected in the UI by posting messages when tasks are completed or errors occur.

Responsiveness: Balancing multiple background tasks while ensuring a smooth, responsive UI was a key focus. The combination of asynchronous task management and event-driven UI updates allows for a non-blocking user experience.

This approach enables the TUI to offer a fluid, non-blocking experience, allowing users to harness the power of LLMs efficiently within structured workflows.

I really enjoy pushing this solution to a higher level, but it's crucial to ensure that this aligns with the first use case it's meant to serve. This balancing act between striving for more enhancements and staying true to the initial use case can be mentally and creatively taxing—especially with all the creative energy and analytical work that has gone into it. The constraints—both mental and creative—bring an emotional challenge, as it means letting go even when there's still visible potential for improvement.

So on that note, this blog post is the finish of this part of coding, and I will start preparing it for its inclusion in the next release.

To finish off, what is the future potential (-;

### Future Potential

One of the more exciting future directions for this solution is integrating a Redis-based approach to enable multi-user functionality. This would allow multiple users to collaborate on the same workflows in real-time, enhancing both scalability and user experience. By leveraging Redis for state management and synchronization, user actions can be consistently reflected across all connected clients, opening up new possibilities for collaborative AI development and shared workflows. Additionally, Redis could facilitate running activated processes even after the TUI has closed, whether through a local or cloud-based solution. These enhancements align with Underdog Cowboy's mission to make sophisticated AI interactions accessible and intuitive, empowering your innovative ideas to thrive and evolve.

