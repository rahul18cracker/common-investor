"""
LLM Prompts & Templates

Collection of prompts for the research agent to perform qualitative analysis.
"""

SYSTEM_PROMPT = """You are an expert financial analyst specializing in qualitative 
analysis of public companies. Your role is to analyze companies using Phil Town's 
Rule #1 investing methodology, focusing on the Four Ms: Meaning, Moat, Management, 
and Margin of Safety.

Your analysis should be:
- Fact-based and grounded in SEC filings and public information
- Objective and balanced, highlighting both strengths and risks
- Clear and concise, suitable for individual investors
- Cited with specific references to source documents

Always provide actionable insights and avoid speculation."""


BUSINESS_ANALYSIS_PROMPT = """Analyze the business model of {company_name} ({ticker}) 
based on their latest 10-K filing.

Focus on:
1. What products/services does the company sell?
2. Who are their primary customers?
3. What are their main revenue streams?
4. How does the business make money?

Provide a clear, concise summary suitable for an investor trying to understand 
if this business falls within their "circle of competence".

SEC Filing Content:
{filing_content}
"""


MOAT_ANALYSIS_PROMPT = """Evaluate the competitive moat of {company_name} ({ticker}).

Assess the following moat types:
1. **Brand Power**: Does the company have strong brand recognition and pricing power?
2. **Network Effects**: Does the product/service become more valuable as more people use it?
3. **Cost Advantages**: Does the company have structural cost advantages over competitors?
4. **Switching Costs**: Is it difficult/expensive for customers to switch to competitors?
5. **Regulatory/IP Barriers**: Does the company have patents, licenses, or regulatory protection?

For each relevant moat type:
- Provide specific evidence from SEC filings
- Rate the strength (Strong/Moderate/Weak)
- Identify threats to the moat

Financial metrics to consider:
- ROIC: {roic_avg}
- Gross Margin: {gross_margin}
- Operating Margin: {operating_margin}

Conclude with an overall moat score (0-10) and explanation.

SEC Filing Content:
{filing_content}
"""


MANAGEMENT_ANALYSIS_PROMPT = """Evaluate the management quality of {company_name} ({ticker}).

Focus on:
1. **Capital Allocation**: How well does management deploy capital?
   - R&D investments
   - Acquisitions track record
   - Share buybacks (accretive or dilutive?)
   - Dividend policy
   
2. **Insider Ownership**: Do executives have significant skin in the game?

3. **Compensation Alignment**: Is executive compensation aligned with shareholder interests?

4. **Communication Quality**: Are earnings calls, 10-Ks, and shareholder letters transparent?

5. **Track Record**: Has management delivered on past promises?

Financial context:
- Debt/Equity: {debt_to_equity}
- Interest Coverage: {interest_coverage}
- Share count trend: {share_count_trend}

Provide specific examples and conclude with a management quality score (0-10).

SEC Filing Content:
{filing_content}
"""


RISK_ANALYSIS_PROMPT = """Identify and analyze the key risk factors for {company_name} ({ticker}).

Categorize risks as:
1. **Business Risks**: Competition, market changes, product obsolescence
2. **Financial Risks**: Debt levels, cash flow volatility, currency exposure
3. **Regulatory Risks**: Government regulation, legal issues, compliance
4. **Operational Risks**: Key person dependencies, supply chain, cybersecurity

For each significant risk:
- Describe the risk clearly
- Assess the likelihood (High/Medium/Low)
- Evaluate potential impact (High/Medium/Low)
- Note any mitigating factors

SEC Filing Risk Factors Section:
{risk_factors_content}
"""


RECOMMENDATION_PROMPT = """Based on the complete qualitative analysis of {company_name} ({ticker}), 
provide an investment recommendation.

Analysis Summary:
- Business Model Score: {business_score}/10
- Moat Score: {moat_score}/10
- Management Score: {management_score}/10
- Overall Risk Level: {risk_level}

Rule #1 Four Ms Assessment:
1. **Meaning**: Does this business fall within my circle of competence?
2. **Moat**: Does it have durable competitive advantages?
3. **Management**: Is management excellent at capital allocation?
4. **Margin of Safety**: What margin of safety is appropriate given the risks?

Provide:
1. Overall qualitative score (0-10)
2. Key strengths (top 3)
3. Key concerns (top 3)
4. Recommended minimum Margin of Safety percentage
5. Brief investment thesis (2-3 sentences)

Remember: This is qualitative analysis only. Investors must also evaluate 
quantitative metrics (ROIC, growth rates, valuation) before making decisions.
"""


# Report Generation Prompts
EXECUTIVE_SUMMARY_PROMPT = """Create a concise executive summary (150-200 words) for 
the qualitative analysis of {company_name} ({ticker}).

Include:
- What the company does (1 sentence)
- Key competitive advantages (1-2 sentences)
- Management quality assessment (1 sentence)
- Primary risks (1-2 sentences)
- Overall investment appeal from a qualitative perspective (1 sentence)

Analysis details:
{analysis_details}
"""
