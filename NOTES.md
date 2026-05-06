May 1: Learned about Github Actions for workflows. These workflows can be used to run scripts automatically and even test out commits sent out to github to make sure these changes haven't introduced new bugs or broken existing functionality.

May 4: I learned the importance of really understanding the spec's decisions and tasks that are being implemented by AI. AI can perform tasks, especially when it is highly specified, but may not completely finish the task especially when having a layered codebase. For example, when wrapping creating a client wrapper to have external calls only be done in these files. Claude did perform this task, moving helper functions in client specific files. But missed functions from other layers of the project such as ingestion which calls out the youtube API. This highlights the importance of fully understanding the spec and monitoring what has been implemented

May 5: Future refactors - create a better system for prompts/keywords instead of having a bunch of different prompts/keywords for each genre. 

Fix to-issues skill, taking out the need for triage for simple tasks (resulting in less tokens)

Learn for possible ways we can use abstraction to manage complexity and keep the project simple. 

Regarding using abstraction to manage complexity, through improve-codebase-architecture I learned that removing abstraction (shallow modules) and turning them into deep modules such as collpasing several thin wrappers into a bigger module would help with simplicity by not introducing too many layers. One pattern to remember is that if understanding one concept requires the need to bounce between many small modules then those modules are shallow (interface is nearly as complex as the implementation). Keep structure simple, fewer pass-throughs, and have complexity concentrated where it belongs.