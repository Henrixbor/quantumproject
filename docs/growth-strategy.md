# Quantum MCP Relayer - Go-to-Market Growth Strategy

**Product**: Quantum-as-a-Service API (3 quantum optimization tools via MCP + REST)
**North Star Metric**: Monthly active API jobs executed
**Date**: March 2026

---

## 1. Launch Strategy

### Phase 1: Pre-Launch Seeding (Week -2 to 0)

**Build waitlist before launch.**

- Create landing page at quantummcp.dev with a live demo widget (paste 3 crypto tickers, get optimized portfolio in 10s)
- Seed 50 beta users from MCP developer communities (Claude Discord, MCP GitHub discussions)
- Collect 5 case study screenshots showing quantum vs. classical results side-by-side
- Pre-write all launch day copy, threads, and assets

### Phase 2: Launch Day Blitz (Day 0)

**ProductHunt Launch Plan**
- Launch Tuesday or Wednesday at 12:01 AM PT (highest upvote windows)
- Tagline: "Add quantum computing to your AI apps in 5 minutes"
- First comment: technical founder story + live demo GIF showing Claude using quantum tools
- Prep 30 supporters to upvote + leave genuine comments in first 2 hours
- Reply to every comment within 15 minutes
- Target: Top 5 Product of the Day (#1 in Developer Tools)
- Expected result: 500-1,000 signups day one

**Hacker News Post**
- Title format: "Show HN: Quantum optimization as MCP tools for Claude"
- Post as Show HN (not a link post) with technical depth: explain QAOA, show architecture diagram, share benchmark numbers
- Post between 8-10 AM ET on a weekday
- Engage authentically in comments -- answer quantum computing skepticism with data
- Have a separate "Ask HN" post ready for week 2: "Ask HN: Has anyone used quantum computing in production?"
- Expected result: 200-400 signups if front page

**Reddit Strategy**
- r/ClaudeAI: "I built MCP tools that give Claude quantum computing abilities" (show conversation screenshot)
- r/MachineLearning: Focus on the QAOA algorithm benchmarks
- r/QuantumComputing: Technical deep-dive on the simulator + Wukong integration
- r/SideProject: Builder story angle
- r/programming: Architecture walkthrough
- Space posts 2-3 days apart to avoid spam perception
- Expected result: 100-200 signups across all subreddits

### Phase 3: Sustained Launch (Week 1-4)

- Submit to MCP tool directories and awesome-mcp lists on GitHub
- Post to Dev.to, Hashnode, and Medium with technical tutorials
- Launch on AlternativeTo, SaaSHub, and BetaList
- Twitter/X thread from founder account showing live quantum results

---

## 2. Growth Channels (Ranked by Expected ROI)

| Rank | Channel | CAC Est. | Scalability | Time to Impact | Priority |
|------|---------|----------|-------------|----------------|----------|
| 1 | MCP ecosystem / Anthropic directory | $0 | High | 2-4 weeks | P0 |
| 2 | Content SEO (quantum + AI keywords) | $5-15 | Very High | 2-6 months | P0 |
| 3 | Developer community (Discord, GitHub) | $2-8 | Medium | 1-3 months | P0 |
| 4 | Referral program | $5-10 | High | 1-2 months | P1 |
| 5 | Technical blog / case studies | $10-20 | High | 1-3 months | P1 |
| 6 | Twitter/X developer audience | $3-12 | Medium | 1-2 months | P1 |
| 7 | YouTube tutorials | $15-30 | High | 3-6 months | P2 |
| 8 | Conference talks (AI/quantum) | $20-50 | Low | 3-6 months | P2 |
| 9 | LinkedIn thought leadership | $10-25 | Medium | 2-4 months | P2 |
| 10 | Paid ads (Google, Twitter) | $30-80 | High | Immediate | P3 |

**Rationale**: The MCP ecosystem is nascent and has minimal competition. Being the first quantum MCP service means organic discovery through Anthropic's directory and MCP-related searches will drive the highest ROI signups with zero spend. Content SEO compounds over time and targets high-intent "quantum optimization API" and "MCP tools for Claude" queries with near-zero competition.

---

## 3. Viral Loop Design

### Free-to-Paid Conversion Engine

```
Free user (10 jobs/mo)
  → Hits limit on day 15-20 (ideal)
  → Sees "Upgrade to unlock 100 jobs" prompt in API response
  → 8-12% convert to Starter ($29)
  → Power users hit 100 limit in month 2-3
  → 15-20% upgrade to Pro ($99)
```

**Key design principle**: Free tier must be generous enough to prove value but restrictive enough to create upgrade pressure. 10 jobs/month means ~2-3 per week, enough to build into a workflow but not enough for production.

### Referral Mechanics

**"Give 20, Get 20" Program**
- Referrer gets 20 bonus jobs added to their monthly quota
- Referred user gets 20 bonus jobs on their first month (total 30 free)
- Referral link embedded in every API response JSON: `"_referral": "quantummcp.dev/r/USER_ID"`
- Dashboard shows referral stats and earned bonus jobs

**Built-in Virality Triggers**
1. **Result watermark**: Free tier API responses include `"powered_by": "Quantum MCP Relayer"` field -- developers leave this in their apps, creating passive awareness
2. **Comparison badge**: Auto-generated image comparing quantum vs. classical result that users can embed/share
3. **GitHub badge**: "Quantum-Powered" badge for README files of projects using the API
4. **MCP config sharing**: When developers share their Claude MCP configs (common in the community), our server appears in their setup

**Target viral coefficient**: K = 0.3 at launch, K = 0.6 by month 6 (each user brings 0.6 new users on average).

---

## 4. Funnel Optimization

### Full Funnel Map

```
AWARENESS          INTEREST           TRIAL              ACTIVATION          PAID
Blog/HN/PH ──→ Landing page ──→ API key signup ──→ First API call ──→ Upgrade
  100%             40% CTR          25% signup         60% activate      8-12% convert
```

### Stage-by-Stage Optimization

**Awareness to Interest (Target: 40% CTR)**
- Lead with concrete numbers: "2-3x better Sharpe ratios" not "quantum computing"
- Show before/after comparisons, not architecture diagrams
- Headline test: "Quantum" vs. "2x Better Optimization" (hypothesis: specific results outperform buzzwords)

**Interest to Trial (Target: 25% signup rate)**
- One-click signup: GitHub OAuth only (no email/password friction)
- Show API key immediately after signup -- no email verification required
- Live playground on landing page: enter 3 stock tickers, see quantum-optimized portfolio in 10 seconds without signing up

**Trial to Activation (Target: 60% make first API call within 48 hours)**
- Post-signup screen: copy-paste curl command with their API key pre-filled
- "First call in 60 seconds" onboarding email sent immediately
- If no API call within 24 hours: trigger email with a one-click "run sample query" button
- MCP setup wizard: auto-generate claude_desktop_config.json with their key

**Activation to Paid (Target: 8-12% free-to-paid in month 1)**
- Usage meter in dashboard showing jobs remaining
- Email at 80% usage: "You've used 8 of 10 free jobs this month"
- Email at 100% usage: "You've hit your limit. Upgrade for $29/mo to keep optimizing."
- Offer first month at 50% off ($14.50) in the limit-reached email
- Show ROI calculator: "Your 10 queries found $X in portfolio improvements"

### Key Metrics to Track at Each Stage
- Time to first API call (target: < 5 minutes)
- Jobs per user per week in first month
- Day 7 retention (target: 40%)
- Day 30 retention (target: 20%)
- Free-to-paid conversion rate by cohort
- Expansion revenue rate (Starter to Pro, Pro to Business)

---

## 5. Content Marketing Plan

### Content Pillars

| Pillar | Purpose | Frequency |
|--------|---------|-----------|
| Quantum results benchmarks | Prove the value proposition with data | 2x/month |
| MCP ecosystem tutorials | Capture developer search traffic | 2x/month |
| Customer case studies | Social proof for conversion | 1x/month |
| "Quantum for Developers" education | SEO long-tail, build authority | 2x/month |
| Industry optimization examples | Expand TAM awareness | 1x/month |

### Content Calendar (Month 1-3)

**Month 1: Launch Content**
- "How We Built a Quantum API That Gives Claude Superpowers" (founder blog, Dev.to)
- "Quantum vs. Classical Portfolio Optimization: 10,000 Backtest Comparison" (data-heavy, Medium + HN)
- "5-Minute Setup: Add Quantum Computing to Claude Desktop" (tutorial, YouTube + blog)
- "Why MCP is the Right Protocol for Quantum Computing" (thought leadership, blog)

**Month 2: Depth Content**
- "How a Crypto Fund Uses Quantum Optimization to Beat the Market" (case study)
- "QAOA Explained for Software Engineers" (educational, Dev.to)
- "Building a Quantum-Powered Travel Planner with Claude" (tutorial with code)
- "Benchmarking Quantum Route Optimization: 5 to 500 Locations" (technical benchmark)

**Month 3: Expansion Content**
- "10 Problems You Didn't Know Quantum Computing Could Solve" (awareness, broader audience)
- "From Simulator to 72-Qubit Processor: Our Hardware Roadmap" (thought leadership)
- "Quantum Meeting Scheduler vs. Google Calendar: A/B Test Results" (data-driven comparison)
- Guest posts on 2-3 AI/developer publications

### SEO Keyword Targets

| Keyword Cluster | Monthly Search Vol (Est.) | Competition | Priority |
|-----------------|--------------------------|-------------|----------|
| "quantum computing API" | 500-1,000 | Low | P0 |
| "MCP tools for Claude" | 200-500 | Very Low | P0 |
| "portfolio optimization API" | 1,000-2,000 | Medium | P0 |
| "quantum optimization" | 2,000-5,000 | Medium | P1 |
| "route optimization API" | 1,500-3,000 | Medium | P1 |
| "quantum as a service" | 300-800 | Low | P1 |
| "QAOA algorithm" | 500-1,000 | Low | P2 |

### Distribution Channels for Each Piece
1. Publish on own blog (SEO value)
2. Cross-post to Dev.to / Hashnode (reach)
3. Submit to HN if technical enough
4. Twitter/X thread summarizing key findings
5. LinkedIn post for B2B reach
6. Share in Discord + relevant Slack communities

---

## 6. Community Building

### Discord Server Structure

**Channels:**
- `#announcements` -- product updates, new features
- `#showcase` -- users share what they built with quantum tools
- `#help` -- technical support (respond within 2 hours during business hours)
- `#feature-requests` -- upvotable feature requests
- `#quantum-curious` -- general quantum computing discussion
- `#benchmarks` -- share and compare optimization results

**Growth Tactics:**
- Invite all beta users and PH/HN signups to Discord
- Weekly "Quantum Office Hours" voice chat (30 min, founder-led)
- Monthly "Build with Quantum" challenge with prizes (free Pro month)
- Bot that posts interesting API results (anonymized) to #showcase

**Target**: 200 members month 1, 500 month 3, 1,500 month 6.

### GitHub Community

- Open-source example projects using Quantum MCP Relayer
- Maintain `awesome-quantum-mcp` list
- Accept community-contributed MCP tool wrappers
- Respond to all issues within 24 hours
- Star-gate: exclusive beta features for repos with 100+ stars that integrate our API
- Sponsor relevant open-source quantum/MCP projects ($200-500/mo)

### Community-Led Growth Flywheel

```
User builds something cool
  → Shares in #showcase
  → We amplify on Twitter/blog
  → Creator gets recognition + bonus jobs
  → Others see what's possible
  → New users sign up to build their own
```

---

## 7. Partnership Strategy

### Tier 1: MCP Ecosystem (Highest Priority)

**Anthropic MCP Directory**
- Submit to official MCP server directory immediately at launch
- Ensure compliance with all MCP spec requirements
- Provide Anthropic team with early access and direct support line
- Goal: become a featured/highlighted MCP server

**MCP Tool Aggregators**
- Submit to Smithery, mcp.so, Glama, and every MCP directory that exists
- Provide custom descriptions and screenshots for each
- Monitor and respond to reviews

### Tier 2: AI Platform Integrations

**Claude / Anthropic**
- Build Claude Desktop plugin for one-click quantum tool installation
- Create "Quantum Claude" demo project Anthropic can reference
- Propose co-marketing: "What becomes possible when AI meets quantum"

**Other AI Assistants**
- Build OpenAI function-calling compatible endpoints (expand TAM)
- LangChain / LlamaIndex tool integrations (pip-installable)
- Cursor IDE integration for quantum-powered code optimization

### Tier 3: Vertical Partnerships

| Partner Type | Value Prop | Target Partners |
|-------------|-----------|-----------------|
| Crypto/DeFi platforms | Quantum portfolio optimization | DeFi protocols, crypto analytics tools |
| Logistics SaaS | Route optimization integration | Fleet management, delivery platforms |
| Scheduling tools | Meeting optimization | Cal.com, Calendly, scheduling startups |
| AI consultancies | White-label quantum tools | AI/ML consulting firms |

### Tier 4: Academic & Research

- Free Business tier for university research groups (in exchange for published benchmarks)
- Co-author papers comparing quantum vs. classical optimization
- Sponsor quantum computing hackathons ($500-1,000 each)

---

## 8. Experiment Backlog (First 60 Days)

| # | Experiment | Hypothesis | Metric | Timeline |
|---|-----------|-----------|--------|----------|
| 1 | Live demo widget on landing page (enter tickers, get result) | Interactive demo increases signup rate by 30% | Signup conversion rate | Week 1-2 |
| 2 | "Quantum vs. Classical" comparison in every API response | Seeing the difference in every response increases retention by 20% | Day 7 retention | Week 1-2 |
| 3 | GitHub OAuth vs. email signup | GitHub-only signup increases completion rate by 40% | Signup completion rate | Week 2-3 |
| 4 | Onboarding email sequence (1, 24h, 72h, 7d) vs. no emails | Email sequence increases activation (first API call) by 25% | Activation rate | Week 2-4 |
| 5 | Free tier: 10 jobs vs. 25 jobs vs. 50 jobs | 10 jobs maximizes paid conversion; 25 maximizes total revenue (more users stay) | Free-to-paid conversion rate, total MRR | Week 3-5 |
| 6 | Usage limit email at 70% vs. 90% vs. 100% | Earlier warning (70%) increases upgrade rate by 15% | Upgrade conversion rate | Week 4-6 |
| 7 | Referral bonus: 10 vs. 20 vs. 50 extra jobs | 20 jobs hits the sweet spot of motivating referrals without cannibalizing paid | Referral rate, K-factor | Week 4-6 |
| 8 | Twitter thread format: technical deep-dive vs. results showcase | Results-focused threads drive 2x more signups | Signups attributed to Twitter | Week 3-5 |
| 9 | Pricing page: show annual discount vs. monthly only | Annual option increases average contract value by 20% | ARPU, annual vs monthly split | Week 5-7 |
| 10 | "Powered by Quantum MCP" badge in free tier responses | Badge drives measurable referral traffic | Referral traffic from badge URLs | Week 6-8 |

**Experiment velocity target**: 2-3 experiments running concurrently, 5+ completed per month.

**Decision criteria**: Each experiment runs until 95% statistical significance OR 2 weeks, whichever comes first. Minimum 100 users per variant.

---

## 9. KPIs & Monthly Targets

### Primary Metrics

| Metric | Month 1 | Month 2 | Month 3 | Month 4 | Month 5 | Month 6 |
|--------|---------|---------|---------|---------|---------|---------|
| Total signups (cumulative) | 500 | 1,200 | 2,500 | 4,000 | 6,500 | 10,000 |
| Monthly active users | 300 | 600 | 1,200 | 2,000 | 3,200 | 5,000 |
| API jobs executed/month | 2,000 | 8,000 | 25,000 | 60,000 | 120,000 | 250,000 |
| Paid customers | 15 | 50 | 130 | 280 | 500 | 850 |
| MRR | $600 | $2,500 | $7,500 | $18,000 | $35,000 | $65,000 |
| Free-to-paid conversion | 5% | 7% | 9% | 10% | 11% | 12% |
| Churn rate (monthly) | 15% | 12% | 10% | 8% | 7% | 6% |
| Viral coefficient (K) | 0.1 | 0.2 | 0.3 | 0.35 | 0.4 | 0.5 |

### Secondary Metrics

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| Time to first API call | < 10 min | < 5 min | < 3 min |
| Day 7 retention | 30% | 40% | 50% |
| Day 30 retention | 15% | 20% | 25% |
| NPS score | 30 | 40 | 50 |
| CAC (blended) | $25 | $15 | $10 |
| LTV (projected) | $150 | $250 | $400 |
| LTV:CAC ratio | 6:1 | 17:1 | 40:1 |
| Discord members | 200 | 500 | 1,500 |
| GitHub stars | 100 | 400 | 1,000 |

### Revenue Breakdown Target (Month 6)

| Tier | Customers | Revenue | % of MRR |
|------|-----------|---------|----------|
| Free | 4,150 | $0 | 0% |
| Starter ($29) | 500 | $14,500 | 22% |
| Pro ($99) | 250 | $24,750 | 38% |
| Business ($499) | 50 | $24,950 | 38% |
| **Expansion + Annual** | -- | **$850** | **1%** |
| **Total** | **4,950** | **$65,050** | **100%** |

---

## 10. Budget Allocation ($5,000/month)

### Month 1-2: Launch Phase

| Category | Amount | Allocation |
|----------|--------|------------|
| Content creation (freelance writers, designers) | $1,500 | 30% |
| ProductHunt / launch campaigns | $500 | 10% |
| Community sponsorships (hackathons, OSS) | $500 | 10% |
| Developer tooling (analytics, email, hosting) | $800 | 16% |
| Paid social experiments (Twitter/X ads) | $700 | 14% |
| Influencer seeding (send to 10 AI devfluencers) | $500 | 10% |
| Reserve / opportunistic spend | $500 | 10% |

### Month 3-4: Growth Phase

| Category | Amount | Allocation |
|----------|--------|------------|
| Content creation + SEO | $1,500 | 30% |
| Paid acquisition (Google Ads on "quantum API" keywords) | $1,200 | 24% |
| Community + events | $700 | 14% |
| Developer tooling + infrastructure | $600 | 12% |
| Partnership development | $500 | 10% |
| Reserve | $500 | 10% |

### Month 5-6: Scale Phase

| Category | Amount | Allocation |
|----------|--------|------------|
| Paid acquisition (scale winning channels) | $2,000 | 40% |
| Content creation + SEO | $1,200 | 24% |
| Community + events | $600 | 12% |
| Developer tooling | $500 | 10% |
| Partnership co-marketing | $400 | 8% |
| Reserve | $300 | 6% |

### Tool Stack (within tooling budget)

| Tool | Cost/mo | Purpose |
|------|---------|---------|
| PostHog (free tier) | $0 | Product analytics, funnels, feature flags |
| Resend | $20 | Transactional + marketing email |
| Plausible | $9 | Privacy-friendly web analytics |
| Cal.com (free) | $0 | Demo booking |
| Typefully | $15 | Twitter/X scheduling and analytics |
| Vercel (free tier) | $0 | Landing page hosting |
| Discord (free) | $0 | Community |
| **Total** | **~$44** | |

---

## Appendix: 90-Day Execution Timeline

### Weeks 1-2: Foundation
- [ ] Ship landing page with live demo widget
- [ ] Set up analytics (PostHog funnels, Plausible)
- [ ] Create GitHub OAuth signup flow
- [ ] Write and schedule first 4 blog posts
- [ ] Submit to MCP directories
- [ ] Launch Discord server
- [ ] Seed 50 beta users

### Weeks 3-4: Launch
- [ ] ProductHunt launch
- [ ] HN Show HN post
- [ ] Reddit campaign (5 subreddits, spaced out)
- [ ] Start onboarding email experiment
- [ ] Begin Twitter/X content cadence (3x/week)
- [ ] Reach out to 10 AI dev influencers

### Weeks 5-8: Optimize
- [ ] Analyze launch cohort data
- [ ] Run free tier limit experiment
- [ ] Launch referral program
- [ ] Publish first case study
- [ ] Start Google Ads on highest-intent keywords
- [ ] First "Quantum Office Hours" Discord event
- [ ] Submit to Anthropic for featured MCP server

### Weeks 9-12: Scale
- [ ] Double down on top 2 acquisition channels
- [ ] Launch annual pricing option
- [ ] First partnership integration live
- [ ] Community "Build with Quantum" challenge
- [ ] Publish benchmark comparison paper
- [ ] Evaluate and kill underperforming channels
- [ ] Plan Month 4-6 based on data

---

*This is a living document. Review and update monthly based on actual performance data. Kill what doesn't work. Double down on what does.*
