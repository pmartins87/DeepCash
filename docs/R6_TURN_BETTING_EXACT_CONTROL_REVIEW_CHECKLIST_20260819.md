# R6 exact turn betting control review checklist — 2026-08-19

Review this branch against the following fail-closed checklist before merge:

- [ ] no opponent private-card identity appears in any decision infoset key;
- [ ] public river chance excludes both private hands and the turn board;
- [ ] every compatible exact deal has its legal public river distribution normalized independently;
- [ ] turn fold payoff uses the pre-bet pot boundary;
- [ ] called turn bets update river pot by `+2b` and stack by `-b`;
- [ ] called turn all-ins bypass river betting;
- [ ] river fold/call payoff uses post-turn pot and matched river bet exactly;
- [ ] counterfactual regret reach uses opponent reach, while average strategy uses own realization reach;
- [ ] alternating P1 update sees the refreshed P0 strategy;
- [ ] action-conditioned range extraction multiplies only own action probabilities;
- [ ] focused tests pass;
- [ ] repository CI passes;
- [ ] no exploitability or R6-PASS claim is made before the exact two-street BR oracle exists.
