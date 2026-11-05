# L2 Search Tokens

Map profile `l2[]` to forum search and gap buckets. Source: [topic-buckets.yaml](../configs/topic-buckets.yaml).

## Usage

Each token → usually **`search_specific_forum_fast`**; see [forum-search-strategy.md](forum-search-strategy.md) for other options.

- Gap Scan: scarcity searches per L2 token set
- Community Similarity: append L2 tokens to `search_query`
- Official appeal titles: include L2 label + one of region/dataset/operator

See [mcp-by-phase.md](mcp-by-phase.md) Phase 4.

## Examples

| L2 | Primary tokens |
|----|----------------|
| PPAC | PPAC, Power Pool, turnover, maxTrade, ts_target_tvr |
| VF | Value Factor, VF, ATOM, pyramid |
| correlation | self-corr, correlation |
| dataset | analyst*, fundamental*, model*, sentiment* |

When multiple L2 tags, union tokens; dedupe searches against quota in quotas-and-cooldown.md.

## angle_slugs

Each bucket lists suggested angles — rotate per content-diversity.md.
