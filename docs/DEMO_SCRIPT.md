# Demo Script

## Goal

Present InsightAI BI in 2 to 3 minutes with a product-focused story that is strong enough for portfolio walkthroughs and technical interviews.

Best entry point:

- open `http://localhost:5173/demo`

The `/demo` route requires no login and already contains:

- a representative dataset
- Ask AI output
- ranked insights
- dashboard narrative
- a saved dashboard layout

## 2–3 Minute Flow

### 1. Open `/demo` and frame the product

What to say:

- `InsightAI BI is a Business Intelligence product designed to combine AI speed with BI structure.`
- `Instead of treating analytics as disposable chat, it turns useful outputs into refreshable dashboard assets.`

What to point at:

- demo dataset summary
- suggested prompts
- overview copy that explains demo mode

### 2. Show Ask AI

What to show:

- the natural-language question
- the generated answer
- the SQL-backed result
- the chart and result table

What to say:

- `Ask AI is not just text generation. It produces a SQL-backed answer over the dataset.`
- `That keeps the workflow more auditable than a pure chat UI because the answer is grounded in a query result.`

### 3. Show the Insight Engine

What to show:

- ranked insight cards
- insight narrative summary
- different analytical patterns such as distribution, top performer, correlation, or outlier

What to say:

- `The platform also runs a deterministic Insight Engine.`
- `It scores columns, generates candidate findings, removes duplicates, ranks what matters most, and produces a narrative summary.`

### 4. Show the dashboard

What to show:

- widget grid
- multiple visualization types
- dashboard narrative
- freshness status

What to say:

- `The key product move is persistence.`
- `Ask AI results and generated insights do not disappear after a chat. They can be saved as dashboard widgets with layout, refresh behavior, and narrative.`

### 5. Close with operational capabilities

What to mention briefly:

- `Dashboards can refresh manually or on a schedule.`
- `They expose freshness metadata so the user can see whether the view is current.`
- `They can be exported to PDF.`
- `They can also be shared through secure read-only public links.`

## 30-Second Version

Use this if the interviewer wants the shortest possible explanation:

`InsightAI BI is a full-stack analytics product where users upload datasets, ask SQL-backed AI questions, generate ranked insights automatically, save the best outputs into persistent dashboards, refresh them over time, and share the result safely through read-only links.`

## If You Have Extra Time

After the main walkthrough, mention:

- authenticated users can upload their own CSV datasets
- the backend persists query history and dashboard widgets
- refresh is backed by a worker loop and freshness metadata
- the frontend uses route lazy loading and chunk splitting for heavier dependencies

## Interview Emphasis

If the conversation becomes more technical, emphasize these points in order:

1. Ask AI is SQL-backed, not a pure chat answer
2. Insight generation is deterministic-first and does not fully depend on LLM availability
3. Dashboards are persistent, refreshable, and shareable
4. The frontend is a real product surface, not just a prototype screen
