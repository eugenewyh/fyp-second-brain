[home](https://www.langchain.com/)

Products

[LangSmith Platform](https://www.langchain.com/langsmith-platform)

Agent Improvement

[![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6a1c6031b3db015796401c5b_LangSmith%20Engine_Icon_light%201.svg)\\
\\
Engine\\
\\
Improve agents autonomously](https://www.langchain.com/langsmith/engine) [![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6989c024180a65887312dd40_Frame%202147254707.svg)\\
\\
Observability\\
\\
See exactly what your agents are doing](https://www.langchain.com/langsmith/observability) [![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6989c0247f235ca5583fa63b_Frame%202147255166.svg)\\
\\
Evaluation\\
\\
Score and improve agent performance](https://www.langchain.com/langsmith/evaluation)

Agent Infrastructure

[![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6989c024926f877c1de6e728_updated.svg)\\
\\
Deployment\\
\\
Ship and scale agents in production](https://www.langchain.com/langsmith/deployment) [![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6a020888f9b2346912c07f41_sandboxes_light_mode%202.svg)\\
\\
Sandboxes\\
\\
Run agent-generated code safely](https://www.langchain.com/langsmith/sandboxes)

No-Code Agents

[![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/69baea024a5f7c2d229815b0_LangSmith%20Fleet_icon_light%20mode%203.svg)\\
\\
Fleet\\
\\
Agents for the whole company](https://www.langchain.com/langsmith/fleet)

Open Source Frameworks

[![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6989c02453d869396317aaa3_updated-1.svg)\\
\\
deepagents\\
\\
Build long-running agents for complex tasks](https://www.langchain.com/deep-agents) [![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6989c024c2d98286a8fb058f_Frame%202147255166-1.svg)\\
\\
langgraph\\
\\
Build reliable agents with low-level control](https://www.langchain.com/langgraph) [![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/6989c024409fcfc7e5b8f78f_Frame%202147254707-1.svg)\\
\\
langchain\\
\\
Quick start agents with any model provider](https://www.langchain.com/langchain)

Learn

Resources

[Blog](https://www.langchain.com/blog) [Customer Stories](https://www.langchain.com/customers) [Guides](https://www.langchain.com/resources) [Max Agency](https://www.youtube.com/playlist?list=PLfaIDFEXuae3UwB1QGEjsRAr8BzCQss7s)

How-To

[LangChain Academy](https://academy.langchain.com/) [YouTube](https://www.youtube.com/@LangChain) [Documentation](https://docs.langchain.com/)

Community

[LangSmith for Startups](https://www.langchain.com/startups) [Meetups](https://luma.com/langchain?k=c) [Community](https://www.langchain.com/community)

[Docs](https://docs.langchain.com/)

Company

[About](https://www.langchain.com/about) [Careers](https://www.langchain.com/careers) [Partners](https://www.langchain.com/langchain-partner-network) [Events](https://www.langchain.com/events)

[Pricing](https://www.langchain.com/pricing)

[Try LangSmith](https://smith.langchain.com/) [Get a demo](https://www.langchain.com/contact-sales)

[Try LangSmith](https://smith.langchain.com/)

[Get a demo](https://www.langchain.com/contact-sales)

[Agent Architecture](https://www.langchain.com/blog?category_equal=%5B%22Agent+Architecture%22%5D)

# LangGraph Studio: The first agent IDE

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69d50051c5c24f19b81fd73a_Group%202147239256-2.svg)

The LangChain Team

August 1, 2024

![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/69ce2c533137196179bae949_Icon-7.svg)

4

min

[Go back to blog](https://www.langchain.com/blog)

[LangGraph: Balancing agent control with agency](https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide#langgraph-balancing-agent-control-with-agency)

[LangGraph Studio: Visualize and interact with agent graphs for quick iteration](https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide#langgraph-studio-visualize-and-interact-with-agent-graphs-for-quick-iteration)

[How to use LangGraph Studio](https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide#how-to-use-langgraph-studio)

[Conclusion](https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide#conclusion)

Share

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69cbaf7403935dbc92df45ea_Screenshot-2024-07-31-at-8.00.36-PM-1.png)

LLMs have paved the way for the development of new types of _agentic_ applications — and as LLM applications evolve, so must the tooling needed to efficiently develop them. Today, we're announcing LangGraph Studio - the first IDE designed specifically for agent development - in open beta.

LangGraph Studio offers a new way to develop LLM applications, providing a specialized agent IDE for visualizing, interacting with, and debugging complex agentic applications. In this blog, we'll give a brief overview of LangGraph and then explore how LangGraph Studio streamlines the development of agentic applications.

## LangGraph: Balancing agent control with agency

In [January 2023](https://blog.langchain.com/langgraph/), we launched LangGraph, a highly controllable, low-level orchestration framework for building agentic applications. Since then, we've seen teams build more complex agentic applications for production; in turn, we've heavily invested in LangGraph, leading to [a stable 0.1 release](https://blog.langchain.com/langgraph-cloud/) this past June.

LangGraph features a persistence layer that enables human-in-the-loop interactions, and it excels at building complex (i.e. more than a single LLM call) applications that require highly domain-specific cognitive architecture. Most of the agents we see in production fit this description.

LangGraph is fully open source, available in both [Python](https://github.com/langchain-ai/langgraph?ref=blog.langchain.com) and [Javascript](https://github.com/langchain-ai/langgraphjs?ref=blog.langchain.com). It works with or without LangChain, and integrates seamlessly with LangSmith.

## LangGraph Studio: Visualize and interact with agent graphs for quick iteration

While LangGraph offers a new framework for developing agentic applications, we also strongly believe that new tooling is needed to make the development process easier. Building LLM applications differs from traditional software development, requiring different tooling outside of the traditional code editor.

Coding is still important to developing LLM applications — after all, production-ready LangGraph applications have complicated custom logic in the nodes and edges of the graphs that are created. We don't aim to replace code editors but, instead, to **augment** the development experience with tools tailored for LangGraph applications.

LangGraph Studio facilitates this by making it easy to visualize and interact with agent graphs, even if development still primarily happens in code. Visualizing graphs helps developers understand their structure. Furthermore, you can modify an agent result (or the logic underlying a specific node) halfway through the agent's trajectory. This creates an iterative process, by letting you interact with and manipulate the state at that point in time.

While there is much more to explore, we're excited to introduce LangGraph Studio to start with bringing some of the core features of an agent IDE to the world.

## How to use LangGraph Studio

LangGraph Studio is a desktop app, currently available for Apple Silicon. You can download a version [here](https://github.com/langchain-ai/langgraph-studio?ref=blog.langchain.com). Support for more platforms is coming soon.

After you download and open LangGraph Studio, you will be prompted to log in with your LangSmith account. All users of LangSmith (including those with free accounts) currently have access to LangGraph Studio while it is in beta. You can sign up for a LangSmith account [here](https://smith.langchain.com/?ref=blog.langchain.com).

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69cbaf7503935dbc92df45f1_login_screen.png)

After downloading LangSmith, you can open a directory. At a bare minimum, this directory needs to contain a Python file with a graph defined in it.

Next, you will need to create a `langgraph.json` file containing details such as where the agent is defined, which dependencies to install, and which environment variables to load. This file can be created in the UI, or can exist as a file in the directory already. For an example repository which meets these requirements, see [this GitHub repo](https://github.com/langchain-ai/langgraph-example?ref=blog.langchain.com).

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69cbaf7503935dbc92df45fb_select_project_screen.png)

After you open a directory, we will build an environment for you agent to run. After it builds, you should see a visualization of the graph along with a box for interacting with the agent.

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69cbaf7503935dbc92df45f6_graph_screen.png)

When you interact with the agent, you'll get a stream of real-time information about what steps are happening. You can see the agent decide which tools to call, call those tools, and then continue looping.

You can interrupt the agent at any time if veers off course, or you can interrupt the agent to run it in a “debug mode” where it pauses after each step of the graph (so you can walk-through step by step).

0:00 /0:191×

💡

At any point, you can interact with the **state** of the agent.

If you don’t like what the agent responded with at a specific step, you can directly modify the response and then continue with that new response. This can be useful for simulating what would have happened if the agent or a tool returned something different.

0:00 /0:141×

You can also modify the underlying code and then replay the node. LangGraph Studio detects changes to the underlying code files, allowing you to update prompts in your code editor and rerun nodes if an agent responds poorly. This can make it much easier to iterate on long-running agents.

0:00 /0:201×

## Conclusion

Building agentic applications differs from traditional software development. While code editors remain important, new IDEs designed for agents are also needed. LangGraph Studio is a step in this direction, and we're excited to see how it enhances your workflow.

**For more on LangGraph Studio, check out our** [**documentation**](https://github.com/langchain-ai/langgraph-studio?ref=blog.langchain.com). **You can also watch a** [**video walkthrough on YouTube**](https://www.youtube.com/watch?v=pLPJoFvq4_M&ref=blog.langchain.com) **if that's more your style. You can** [**sign up for LangSmith**](https://smith.langchain.com/?ref=blog.langchain.com) **today to try out LangGraph Studio for free.**

**We'd also love your feedback - drop us a line at hello@langchain.dev or on** [**Twitter**](https://x.com/LangChainAI?ref=blog.langchain.com) **to share your thoughts.**

### Related content

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/6a45048d1529692d7efa564b_100.png)

Deep Agents

Agent Architecture

Open Source

#### How to Use RLMs in Deep Agents

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69dcee60745f0e15b18ad4d5_sydney-runkle.png)

Sydney Runkle

July 1, 2026

![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/69cd1fd0002272ce39bf1241_Icon-6.svg)

8

min

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/6a43cc5767154e5584cb825f_dark-57%20characters%20max.png)

Agent Architecture

Deep Agents

Open Source

#### Running Untrusted Agent Code Without a Sandbox

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69e12735c02bb07c894a067a_hunter-lovell.png)

Hunter Lovell

June 30, 2026

![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/69cd1fd0002272ce39bf1241_Icon-6.svg)

6

min

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/6a4293b98a5fbb8e632a9116_98.png)

Open Source

Deep Agents

Agent Architecture

#### Introducing Dynamic Subagents in Deep Agents

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69dcee60745f0e15b18ad4d5_sydney-runkle.png)

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69e12775881c2a7fc9aba41e_colin-francis.png)

![](https://cdn.prod.website-files.com/65c81e88c254bb0f97633a71/69e12735c02bb07c894a067a_hunter-lovell.png)

S. Runkle,

C. Francis,

H. Lovell

June 29, 2026

![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/69cd1fd0002272ce39bf1241_Icon-6.svg)

9

min

![](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/69ce01ea562f8cc223cabf25_Frame%202147254328.svg)

Sign up for our newsletter to stay up to date

Thank you! Your submission has been received!

Oops! Something went wrong while submitting the form.

### S    e    e        w    h    a    t        y    o    u    r        a    g    e    n    t        i    s        r    e    a    l    l    y        d    o    i    n    g

LangSmith, our agent engineering platform, helps developers debug every agent decision, eval changes, and deploy in one click.

[Try LangSmith](https://smith.langchain.com/) [Get a demo](https://www.langchain.com/contact-sales)

###### Products

[LangSmith Platform](https://www.langchain.com/langsmith-platform) [LangSmith Observability](https://www.langchain.com/langsmith/observability) [LangSmith Evaluation](https://www.langchain.com/langsmith/evaluation) [LangSmith Deployment](https://www.langchain.com/langsmith/deployment) [LangSmith Fleet](https://www.langchain.com/langsmith/fleet) [LangSmith Sandboxes](https://www.langchain.com/langsmith/sandboxes) [Deep Agents](https://www.langchain.com/deep-agents) [LangChain](https://www.langchain.com/langchain) [LangGraph](https://www.langchain.com/langgraph)

###### Resources

[Blog](https://www.langchain.com/blog) [Customer Stories](https://www.langchain.com/customers) [Guides](https://www.langchain.com/resources) [Community](https://www.langchain.com/join-community) [Changelog](https://changelog.langchain.com/) [Docs](https://docs.langchain.com/) [Support](https://support.langchain.com/) [LangChain Academy](https://academy.langchain.com/)

###### Company

[About](https://www.langchain.com/about) [Careers](https://www.langchain.com/careers) [Partners](https://www.langchain.com/langchain-partner-network) [Trust Center](https://trust.langchain.com/) [Marketing Assets](https://drive.google.com/drive/folders/1cc_Wdd8k7J5wUONBMvtfIZH_BaYvonym)

[Events](https://www.langchain.com/events)

###### Sign up for our newsletter to stay up to date

Thank you! Your submission has been received!

Oops! Something went wrong while submitting the form.

[All systems operational](https://status.smith.langchain.com/)

[Privacy policy](https://www.langchain.com/privacy-policy) [Terms of service](https://www.langchain.com/terms-of-service)