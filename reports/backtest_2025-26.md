# Backtest: 2025-26 regular season

Settings were chosen on 2024-25 and then frozen, so these are honest out-of-sample results. Each day the model only knew games played before that day.

| Predictor | Games | Picked winner | Brier (lower is better) | Log loss (lower is better) | Avg miss on margin (pts) |
|---|---|---|---|---|---|
| **Model** | 1225 | 68.1% | 0.204 | 0.594 | 11.4 |
| Model, after the first 2 weeks | 1123 | 68.5% | 0.203 | 0.591 | 11.4 |
| Always pick the home team | 1225 | 55.4% | 0.249 | 0.692 | — |
| Pick the better record | 1225 | 66.6% | 0.223 | 0.637 | — |
| Model, Pacers games only | 82 | 70.7% | 0.197 | 0.581 | 11.0 |

## Model vs Vegas (DraftKings lines, games where a line was available)

| Predictor | Games | Picked winner | Brier | Log loss | Avg miss on margin (pts) |
|---|---|---|---|---|---|
| **Model** | 969 | 67.7% | 0.206 | 0.600 | 11.6 |
| Vegas (moneyline, vig removed) | 969 | 69.3% | 0.194 | 0.570 | — |

## Against the spread

If you had taken the model's side against the Vegas spread. Break-even at standard pricing is about 52.4%.

| Games picked | Games | Model's side covered |
|---|---|---|
| Every game | 974 | 47.7% |
| Model disagrees by 2+ pts | 561 | 46.3% |
| Model disagrees by 4+ pts | 266 | 46.6% |

## Calibration: are the percentages honest?

| Favorite's predicted chance | Games | Predicted | Actually won |
|---|---|---|---|
| 50-60% | 438 | 55.0% | 55.3% |
| 60-70% | 366 | 64.9% | 68.6% |
| 70-80% | 241 | 74.9% | 77.6% |
| 80-90% | 158 | 84.3% | 85.4% |
| 90-100% | 22 | 91.6% | 86.4% |

## Settings chosen

- Recency half-life: 30 days
- Shrink toward average (ridge): 2.0
- Weight on last season's games: 0.25
- Typical miss on a game's margin (sigma): 13.9 pts

## End-of-season adjusted ratings (points per 100 possessions)

| Rank | Team | Off rating | Def rating | Net | Pace |
|---|---|---|---|---|---|
| 1 | SAS | 118.2 | 108.3 | +9.9 | 102.6 |
| 2 | OKC | 115.9 | 106.3 | +9.5 | 102.0 |
| 3 | BOS | 117.6 | 108.7 | +8.9 | 97.7 |
| 4 | CHA | 117.5 | 109.0 | +8.5 | 98.4 |
| 5 | DET | 115.6 | 107.4 | +8.2 | 102.3 |
| 6 | NYK | 116.5 | 109.9 | +6.6 | 97.6 |
| 7 | DEN | 120.9 | 114.3 | +6.6 | 103.0 |
| 8 | HOU | 115.4 | 110.6 | +4.8 | 100.0 |
| 9 | ATL | 114.5 | 109.9 | +4.6 | 103.8 |
| 10 | TOR | 114.5 | 110.4 | +4.0 | 100.8 |
| 11 | LAL | 115.4 | 112.1 | +3.3 | 100.3 |
| 12 | CLE | 116.7 | 114.2 | +2.5 | 101.7 |
| 13 | POR | 110.9 | 108.8 | +2.2 | 102.8 |
| 14 | MIN | 113.0 | 110.9 | +2.1 | 103.6 |
| 15 | PHX | 112.3 | 110.4 | +1.9 | 99.7 |
| 16 | LAC | 114.6 | 113.2 | +1.5 | 99.8 |
| 17 | ORL | 111.9 | 111.0 | +0.9 | 104.2 |
| 18 | MIA | 116.2 | 115.4 | +0.8 | 105.0 |
| 19 | PHI | 111.5 | 112.0 | -0.5 | 103.0 |
| 20 | NOP | 112.1 | 114.9 | -2.8 | 104.0 |
| 21 | GSW | 111.4 | 115.0 | -3.6 | 101.2 |
| 22 | DAL | 110.4 | 116.2 | -5.8 | 105.2 |
| 23 | IND | 111.0 | 116.9 | -5.8 | 103.8 |
| 24 | CHI | 109.0 | 115.6 | -6.6 | 106.7 |
| 25 | UTA | 109.9 | 118.4 | -8.6 | 106.4 |
| 26 | SAC | 110.7 | 119.5 | -8.8 | 101.0 |
| 27 | MIL | 109.9 | 118.9 | -8.9 | 99.5 |
| 28 | MEM | 108.7 | 119.8 | -11.0 | 104.5 |
| 29 | WAS | 108.9 | 120.7 | -11.8 | 104.8 |
| 30 | BKN | 103.9 | 116.5 | -12.5 | 100.3 |
