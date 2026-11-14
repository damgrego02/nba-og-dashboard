# Backtest: 2025-26 regular season

Settings were chosen on 2024-25 and then frozen, so these are honest out-of-sample results. Each day the model only knew games played before that day.

| Predictor | Games | Picked winner | Brier (lower is better) | Log loss (lower is better) | Avg miss on margin (pts) |
|---|---|---|---|---|---|
| **Model** | 1229 | 68.2% | 0.204 | 0.594 | 11.4 |
| Model, after the first 2 weeks | 1127 | 68.6% | 0.203 | 0.591 | 11.4 |
| Always pick the home team | 1229 | 55.5% | 0.249 | 0.691 | — |
| Pick the better record | 1229 | 66.6% | 0.223 | 0.637 | — |
| Model, Pacers games only | 82 | 70.7% | 0.197 | 0.581 | 11.0 |

## Model vs Vegas (DraftKings lines, games where a line was available)

| Predictor | Games | Picked winner | Brier | Log loss | Avg miss on margin (pts) |
|---|---|---|---|---|---|
| **Model** | 969 | 67.8% | 0.206 | 0.600 | 11.6 |
| Vegas (moneyline, vig removed) | 969 | 69.3% | 0.194 | 0.570 | — |

## Against the spread

If you had taken the model's side against the Vegas spread. Break-even at standard pricing is about 52.4%.

| Games picked | Games | Model's side covered |
|---|---|---|
| Every game | 974 | 47.8% |
| Model disagrees by 2+ pts | 566 | 46.8% |
| Model disagrees by 4+ pts | 265 | 46.0% |

## Calibration: are the percentages honest?

| Favorite's predicted chance | Games | Predicted | Actually won |
|---|---|---|---|
| 50-60% | 440 | 55.0% | 55.5% |
| 60-70% | 367 | 64.8% | 68.9% |
| 70-80% | 243 | 74.9% | 77.4% |
| 80-90% | 157 | 84.3% | 85.4% |
| 90-100% | 22 | 91.6% | 86.4% |

## Settings chosen

- Recency half-life: 30 days
- Shrink toward average (ridge): 2.0
- Weight on last season's games: 0.25
- Typical miss on a game's margin (sigma): 13.9 pts

## End-of-season adjusted ratings (points per 100 possessions)

| Rank | Team | Off rating | Def rating | Net | Pace |
|---|---|---|---|---|---|
| 1 | SAS | 118.3 | 108.3 | +9.9 | 102.6 |
| 2 | OKC | 115.9 | 106.4 | +9.5 | 102.0 |
| 3 | BOS | 117.6 | 108.7 | +8.9 | 97.7 |
| 4 | CHA | 117.5 | 109.0 | +8.5 | 98.4 |
| 5 | DET | 115.6 | 107.4 | +8.2 | 102.3 |
| 6 | STARS | 114.4 | 107.1 | +7.2 | 34.4 |
| 7 | NYK | 116.6 | 110.0 | +6.6 | 97.6 |
| 8 | DEN | 120.9 | 114.3 | +6.6 | 103.0 |
| 9 | HOU | 115.4 | 110.7 | +4.8 | 100.0 |
| 10 | ATL | 114.5 | 110.0 | +4.6 | 103.8 |
| 11 | TOR | 114.5 | 110.5 | +4.0 | 100.8 |
| 12 | LAL | 115.5 | 112.2 | +3.3 | 100.3 |
| 13 | CLE | 116.7 | 114.2 | +2.5 | 101.7 |
| 14 | POR | 111.0 | 108.8 | +2.2 | 102.8 |
| 15 | MIN | 113.1 | 111.0 | +2.1 | 103.6 |
| 16 | PHX | 112.4 | 110.5 | +1.9 | 99.7 |
| 17 | LAC | 114.7 | 113.2 | +1.5 | 99.8 |
| 18 | ORL | 112.0 | 111.0 | +0.9 | 104.2 |
| 19 | MIA | 116.2 | 115.4 | +0.8 | 105.0 |
| 20 | SHQ | 113.3 | 113.3 | +0.0 | 32.5 |
| 21 | CAN | 113.3 | 113.3 | -0.0 | 34.7 |
| 22 | KEN | 113.3 | 113.3 | -0.0 | 31.5 |
| 23 | CHK | 113.3 | 113.3 | -0.0 | 30.9 |
| 24 | PHI | 111.5 | 112.0 | -0.5 | 103.0 |
| 25 | WORLD | 115.1 | 116.2 | -1.1 | 33.2 |
| 26 | NOP | 112.2 | 115.0 | -2.8 | 104.0 |
| 27 | GSW | 111.4 | 115.0 | -3.6 | 101.2 |
| 28 | DAL | 110.4 | 116.2 | -5.8 | 105.2 |
| 29 | IND | 111.1 | 116.9 | -5.8 | 103.8 |
| 30 | STRIPES | 112.6 | 118.8 | -6.2 | 33.4 |
| 31 | CHI | 109.0 | 115.7 | -6.6 | 106.7 |
| 32 | UTA | 109.9 | 118.5 | -8.6 | 106.4 |
| 33 | SAC | 110.8 | 119.6 | -8.8 | 101.0 |
| 34 | MIL | 110.0 | 118.9 | -8.9 | 99.5 |
| 35 | MEM | 108.8 | 119.8 | -11.0 | 104.5 |
| 36 | WAS | 109.0 | 120.8 | -11.8 | 104.8 |
| 37 | BKN | 104.0 | 116.5 | -12.5 | 100.3 |
