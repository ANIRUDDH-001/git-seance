### gemma3:270m

| setup | replies with no invented facts | unsupported claim rate | answered the question | admitted what git doesn't know | said nothing | median s/reply |
|---|---|---|---|---|---|---|
| naive | 44% | 12% | 23% | 6% | 33% | 2.5 |
| whisper | 86% | 5% | 18% | 6% | 40% | 0.9 |
| guarded | 85% | 6% | 8% | 7% | 43% | 0.6 |
### gemma3:1b

| setup | replies with no invented facts | unsupported claim rate | answered the question | admitted what git doesn't know | said nothing | median s/reply |
|---|---|---|---|---|---|---|
| naive | 56% | 34% | 87% | 9% | 0% | 6.3 |
| whisper | 81% | 10% | 74% | 18% | 0% | 4.1 |
| guarded | 90% | 6% | 69% | 16% | 0% | 3.2 |
### gemma3:4b

| setup | replies with no invented facts | unsupported claim rate | answered the question | admitted what git doesn't know | said nothing | median s/reply |
|---|---|---|---|---|---|---|
| naive | 69% | 16% | 81% | 57% | 0% | 29.9 |
| whisper | 92% | 2% | 86% | 93% | 0% | 28.3 |
| guarded | 96% | 1% | 81% | 97% | 0% | 9.3 |

_Re-scored with the fixed answer checker (spelled-out years count): `python3 scripts/eval.py --rescore`. Same replies, same rules for every setup._
