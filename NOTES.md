May 1: Learned about Github Actions for workflows. These workflows can be used to run scripts automatically and even test out commits sent out to github to make sure these changes haven't introduced new bugs or broken existing functionality.

May 4: I learned the importance of really understanding the spec's decisions and tasks that are being implemented by AI. AI can perform tasks, especially when it is highly specified, but may not completely finish the task especially when having a layered codebase. For example, when wrapping creating a client wrapper to have external calls only be done in these files. Claude did perform this task, moving helper functions in client specific files. But missed functions from other layers of the project such as ingestion which calls out the youtube API. This highlights the importance of fully understanding the spec and monitoring what has been implemented

May 5: Future refactors - create a better system for prompts/keywords instead of having a bunch of different prompts/keywords for each genre. 

Fix to-issues skill, taking out the need for triage for simple tasks (resulting in less tokens)

Learn for possible ways we can use abstraction to manage complexity and keep the project simple. 

Regarding using abstraction to manage complexity, through improve-codebase-architecture I learned that removing abstraction (shallow modules) and turning them into deep modules such as collpasing several thin wrappers into a bigger module would help with simplicity by not introducing too many layers. One pattern to remember is that if understanding one concept requires the need to bounce between many small modules then those modules are shallow (interface is nearly as complex as the implementation). Keep structure simple, fewer pass-throughs, and have complexity concentrated where it belongs.

Found out that Sonnet 4.6 is great for implementing code. 
Use Opus 4.6 to create create specs, break down tasks (to-issues), and traige. But use Sonnet 4.6 for code implementation, as it uses up less tokens.
Can even use auto model in cursor when tasks are simple and well documented (saves the most tokens)

May 11: When implementing core features, ask these questions:
1. - Why are we building this feature? (anchor the feature to business value)
2. - What are we actually building? (functional requirements)
3. - How well should it work? (non-functional requirements)
4. - How do the systems tal to each other? (integration complexity)
5. - What data is involved? (data decisions are one of the heardest to reverse)
6. - Should this feature be built? (is this solving a user need or just a engineering problem?)

May 12: Issues -
1. inconsistent severity and frequency, need to use actual metrics instead of relying on LLM
2. similar problems are being flagged as new instead of known
3. duplicate issues are being stored in insights database
4. incomplete rag, currently have generate -> retrieve -> store. rag is retrieve -> augment -> generate. need to implement pre-extraction prompt injection 
5. vector similaries are not as accurate as expected.

May 13: Issues - 
1. automatic app/youtube pipelines dont write to supabase insights table (fixed)
2. automatic app does not provide much information, usually has no issues. (fixed, used mostHelpful sorting)
3. automatic pipeline does not update keys if already found in the database (fixed)
4. add to frontend "no insights found" (fixed)

Noticed that deleting data on supabase takes a long time, but it is fine as we are only deleting data during the automatic workflow which the user will not affect the user.

Current goals: fix rag and optimize preprocessing for analyzing and tokens
s
Issues: 
- RAG update/insert does not work well. getting inserts for existing problems (might have to lower constant similarity) (fixed)
- Sometimes says rag update: exisitng problem matched but would still insert new data (fixed)
- Cleaned data does not remove emojis (update preprocessing)
- Prior insights is always empty (fixed) - cleaned data as a whole was being compared to the insights, this would result in never getting any prior insights. Changed this so that we run two extract insights, one to bundle insights from cleaned_data, afterwards we get similar insights to the bundle insights and extract insights once more (tradeoff: 2x LLM cost + latency)
- RAG right now only nudges severity/frequency for recurring issues and attaches recurrence tag. add more use cases for rags

May 16:
I have to relook at my project. Right now it feels like I went away from what my intended purpose was for this project by trying to add as many features as possible. It is time to scope down and build back up slowly.

Plans:
- Create a PRD to define the purpose, requirements, features, audience, and current/future scope.
- Create a C4 model diagram to better understand the current architecture and flow of data. It will also help me with future feature design.
- Reorganize my AI Workflow files for better context hopping

What I learned:
- My current project is a URL-in, problems-out analyzer. Right now, we paste either a youtube/AppStore URL and get a rannked list of problems for a single source. The weekly cron would do the same thing for the top-N items in specific categories.

- Through the PRD, I created a clear user and problem. This helped me realize that the current project does not solve the problem. Instead, I scoped down, reinvented

May 27:
Current version:
- Presents weekly insights of the most popular videos/apps in youtube/appstore for specific categories
- Paste a URL-in and get a ranked list of problems for that source.

These features dont solve the target issue which was to help validate if a builder's idea addresses a real user problem.

Version 2.2:
- User inputs their idea and pipeline returns a ranked list of evidence-backed canidate gaps validated through quoted complaints.

