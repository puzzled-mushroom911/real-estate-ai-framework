# Customer Response Skill

## Description
Quick-draft a customer response for {{AGENT_NAME}} that matches their communication style and is backed by accurate local knowledge from the knowledge bases.

## Trigger
Use when asked to: reply to a lead, draft a response, answer a buyer/seller question, handle an objection, or respond to a message.

## Process

1. **Classify the inquiry:**
   - Buyer (hot/warm/cold), seller, general question, objection, or referral
   - Determine response priority and appropriate length

2. **Query knowledge bases:**
   - Conversation history RAG for prior interactions and {{AGENT_NAME}}'s style
   - Neighborhood/market knowledge base for factual accuracy
   - {{AGENT_NAME}}'s YouTube RAG for how they've previously addressed similar topics

3. **Draft the response:**
   - Match {{AGENT_NAME}}'s tone, vocabulary, greeting style, and sign-off
   - Answer the question directly with specific data
   - Include one insight the customer didn't ask for but will value
   - End with an appropriate CTA (soft for cold leads, direct for hot)
   - Keep it proportional to the question length

4. **Verify before delivering:**
   - All facts from knowledge bases (nothing fabricated)
   - Fair Housing compliant
   - No generic realtor language
   - Labeled as DRAFT -- never auto-sent

## Output Format
```
## Response Draft
**To:** [Contact name]
**Type:** [Inquiry classification]
**Priority:** [Immediate / Same Day / 24 Hours]

---
[Ready-to-send message]
---

**Notes:** [Any caveats or items needing {{AGENT_NAME}}'s input]
```
