# Doomsday Proof-of-Escrow for CrewAI

Empower your **CrewAI multi-agent teams** to triage and verify software bounties with cryptographic on-chain proof-of-escrow before assigning development or bug-hunting tasks.

## Multi-Agent Architecture Pattern

In a typical CrewAI setup:
1. **Researcher Agent:** Uses `DoomsdayEscrowVerificationTool` to inspect whether a GitHub issue has authentic escrow on Doomsday L1 / Base.
2. **Planner Agent:** Confirms escrow status and allocates priority based on reward amount.
3. **Coder Agent:** Executes code implementation and prepares Pull Request.

## Quickstart

```python
from crewai import Agent, Task, Crew
from integrations.crewai.doomsday_tool import DoomsdayEscrowVerificationTool

# Tool instance
escrow_tool = DoomsdayEscrowVerificationTool()

# Bounty Triage Agent
triage_agent = Agent(
    role="Bounty Triage Specialist",
    goal="Verify on-chain locked bounty funds before dispatching engineering tasks",
    backstory="You are an expert at identifying genuine paid open-source tasks and protecting compute budget.",
    tools=[escrow_tool],
    verbose=True
)

verify_task = Task(
    description="Verify if GitHub bounty for 'doomsday-network/doomsday#11' has active on-chain escrow.",
    expected_output="A confirmation string specifying whether collateral is verified on Base L2 or Doomsday L1.",
    agent=triage_agent
)

crew = Crew(agents=[triage_agent], tasks=[verify_task])
result = crew.kickoff()
print(result)
```
