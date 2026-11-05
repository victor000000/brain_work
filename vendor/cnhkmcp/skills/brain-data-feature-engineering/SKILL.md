---
name: brain-data-feature-engineering
description: >-
  Automatically analyzes BRAIN dataset fields and generates feature engineering ideas for alpha creation.
  Input: data category, delay, region parameters; Output: markdown document with deep feature engineering suggestions.
  The skill performs autonomous analysis based on dataset and field information, proposing meaningful feature concepts.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - mcp__brain-mcp__get_datasets
  - mcp__brain-mcp__get_datafields
  - mcp__brain-mcp__get_dataset_details
---

# BRAIN Data Feature Engineering Workflow

**Purpose**: Automatically transform BRAIN dataset fields into deep, meaningful feature engineering ideas.

**For Detailed Mindset Patterns**: See `reference.md` for feature engineering philosophy.
**For Implementation Examples**: See `examples.md` for case studies.

## Input Requirements

### Required Parameters:
- **data_category**: Dataset category (e.g., "fundamental", "analyst", "news", "model")
- **delay**: Data delay setting (0 or 1)
- **region**: Market region (e.g., "USA", "EUR", "ASI")

### Optional Parameters:
- **universe**: Trading universe (default: "TOP3000")
- **dataset_id**: Specific dataset ID (if known, skips discovery phase)

## Workflow Overview

### Step 1: Dataset Discovery
**Autonomous Action:**
- Call `mcp__brain-mcp__get_datasets` with parameters (category, delay, region, universe)
- If dataset_id provided: Validate and use it
- If dataset_id not provided: Select the most relevant dataset based on metadata analysis
- **Output**: Locked dataset_id for analysis

### Step 2: Field Extraction and Deconstruction
**Autonomous Action:**
- Call `mcp__brain-mcp__get_datafields` for the selected dataset
- For each field, extract: id, description, dataType, update frequency, coverage
- **Deconstruct each field's meaning**:
  * What is being measured? (the entity/concept)
  * How is it measured? (collection/calculation method)
  * Time dimension? (instantaneous, cumulative, rate of change)
  * Business context? (why does this field exist?)
  * Generation logic? (reliability considerations)
- **Build field profiles**: Structured understanding of each field's essence

### Step 3: Autonomous Thinking and Analysis
**The skill performs deep analysis based on collected information:**

**A. Field Relationship Mapping**
- Analyze logical connections between fields
- Identify: independent fields, related fields, complementary fields
- Map the "story" the dataset tells
- **Key question**: What relationships are implied by these fields?

**B. Question-Driven Feature Generation (Internal Process)**
The skill asks itself these questions and generates feature concepts:

1. **"What is stable?"** → Look for invariants
   - Which fields or combinations remain relatively constant?
   - What stability measures make sense?

2. **"What is changing?"** → Analyze change patterns
   - Rate of change, acceleration, volatility
   - Trend vs. noise separation

3. **"What is anomalous?"** → Identify deviations
   - Outliers, unusual patterns, breaks from normal
   - Deviation magnitude and significance

4. **"What is combined?"** → Examine interactions
   - How fields interact, amplify, or offset each other
   - Synthesis creates new meaning

5. **"What is structural?"** → Study compositions
   - Constituent parts, proportional relationships
   - Structural changes over time

6. **"What is cumulative?"** → Explore accumulation effects
   - Building up over time, decay effects
   - Memory and persistence in data

7. **"What is relative?"** → Make comparisons
   - Relative positioning, ranking, normalization
   - Context within dataset

8. **"What is essential?"** → Distill to core meaning
   - First principles thinking
   - Strip away assumptions, get to essence

**C. Feature Concept Generation**
For each relevant question-field combination:
- Formulate feature concept that answers the question
- Define the concept clearly
- Identify the logical meaning
- Consider directionality (what high/low values mean)
- Identify boundary conditions
- Note potential issues/limitations

### Step 4: Feature Documentation
**For each generated feature concept, document:**
- **Concept Name**: Clear, descriptive name
- **Definition**: One-sentence definition
- **Logical Meaning**: What phenomenon/concept does it represent?
- **Why It's Meaningful**: Why does this feature make sense?
- **Directionality**: Interpretation of high vs. low values
- **Boundary Conditions**: What extremes indicate
- **Data Requirements**: What fields are used and any constraints
- **Potential Issues**: Known limitations or concerns

### Step 5: Output Generation
**Generate structured markdown report including:**

0. **Write the report to ./output_report/region_delay_datasetID_ideas.md** in the following format:

1. **Dataset Understanding**
   - Dataset description and characteristics
   - Field inventory (count, types, update patterns)
   - Key observations about data structure

2. **Field Deconstruction Analysis**
   - For each field: what it truly measures and why
   - Logical relationships between fields
   - "Story" the data tells

3. **Feature Engineering Suggestions by Question Type**

   **3.1 Stability Features**
   - Concepts for measuring stability/invariance
   - Why stability matters in this dataset
   - Example implementations

   **3.2 Change Features**
   - Concepts for capturing change patterns
   - Rate, acceleration, volatility measures
   - Temporal dynamics

   **3.3 Anomaly Features**
   - Deviation and outlier detection concepts
   - Normal vs. abnormal identification
   - Significance measures

   **3.4 Interaction Features**
   - Cross-field interaction concepts
   - Amplification, offset, synthesis effects
   - Combined meaning creation

   **3.5 Structure Features**
   - Composition and relationship concepts
   - Proportional analysis
   - Structural change detection

   **3.6 Cumulative Features**
   - Accumulation and decay concepts
   - Memory/persistence measures
   - Time-weighted effects

   **3.7 Relative Features**
   - Comparison and normalization concepts
   - Ranking and percentile measures
   - Context-relative positioning

   **3.8 Essential Features**
   - First-principles derived concepts
   - Core meaning extraction
   - Fundamental measures

4. **Implementation Considerations**
   - Data quality notes
   - Coverage considerations
   - Computational complexity
   - Potential improvements/extensions

5. **Critical Questions for Further Exploration**
   - What aspects weren't covered?
   - What additional data would be helpful?
   - What assumptions should be challenged?


## Core Analysis Principles

1. **From Data Essence**: Start with what data truly means, not what it's traditionally used for
2. **Autonomous Reasoning**: Skill performs all thinking, no user input required
3. **Question-Driven**: Internal question bank guides feature generation
4. **Meaning Over Patterns**: Prioritize logical meaning over conventional combinations
5. **Transparency**: Show reasoning process in output

## Example Output Structure

When analyzing dataset 'BEME' (Balance Sheet and Market Data), the output would include:

### Dataset Understanding
**Fields Analyzed**: book_value, market_cap, book_to_market, etc.
**Key Observations**: Dataset compares accounting values with market valuations

### Field Deconstruction
- **book_value**: Accountant's calculation of net asset value (quarterly, audited, historical cost-based)
- **market_cap**: Market participants' valuation (continuous, forward-looking, sentiment-influenced)
- **book_to_market**: Ratio comparing these two valuation perspectives

### Feature Concepts Generated

**From "What is stable?"**
- "Market reevaluation stability": Rolling coefficient of variation of book_to_market
- **Logic**: Measures whether market opinion is stable or volatile
- **Meaning**: Stable values suggest consensus, volatile values suggest disagreement/uncertainty

**From "What is changing?"**
- "Value creation vs. market reevaluation decomposition": Separate book_value growth from market_cap growth
- **Logic**: Distinguish fundamental value creation from market sentiment changes
- **Meaning**: Which component drives changes in book_to_market?

**From "What is combined?"**
- "Intangible value proportion": (market_cap - book_value) / enterprise_value
- **Logic**: Quantify proportion of value from intangibles (brand, growth, etc.)
- **Meaning**: What percentage of valuation isn't captured on the balance sheet?

**(Additional question-based features would follow...)**

## Implementation Notes

### The skill should:
1. **Analyze first, then generate**: Fully understand dataset before proposing features
2. **Show reasoning**: Explain why each feature concept makes sense
3. **Be specific**: Reference actual field names and their characteristics
4. **Be critical**: Question assumptions and identify limitations
5. **Be creative**: Look beyond traditional financial metrics

### The skill should NOT:
1. **Ask users to think**: All thinking is internal to the skill
2. **Provide generic templates**: Each analysis should be specific to the dataset
3. **Rely on conventional wisdom**: Challenge traditional approaches
4. **Output patterns without meaning**: Every suggestion must have clear logic

## Quality Assurance

**Self-Check Process:**
- [ ] All fields analyzed, not just skimmed
- [ ] Field meanings understood beyond descriptions
- [ ] Multiple question types explored
- [ ] Each feature has clear logical meaning
- [ ] Reasoning is explicit, not implicit
- [ ] Limitations are acknowledged
- [ ] Output is dataset-specific, not generic

**Validation Questions:**
- Would this analysis help someone truly understand the data?
- Are feature concepts novel yet meaningful?
- Is the reasoning process transparent?
- Does it avoid conventional thinking traps?

---

*This skill performs autonomous deep analysis of BRAIN datasets, generating meaningful feature engineering concepts based on data essence and logical reasoning.*
