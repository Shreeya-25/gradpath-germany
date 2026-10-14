"""Command line interface:  python -m advisor.cli "When is the TUM Informatics deadline?" """
from __future__ import annotations

import argparse

from .agent import Advisor
from .tools import Profile


def main() -> None:
    ap = argparse.ArgumentParser(description="Germany Program Advisor")
    ap.add_argument("question", nargs="*", help="your question")
    ap.add_argument("--cgpa", type=float, default=8.4)
    ap.add_argument("--scale", type=float, default=10.0)
    ap.add_argument("--field", default="Artificial Intelligence and Machine Learning")
    ap.add_argument("--country", default="India")
    ap.add_argument("--gre-quant", type=int, default=None)
    ap.add_argument("--gre-awa", type=float, default=None)
    ap.add_argument("--llm", action="store_true", help="use Claude for generation (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--eval", action="store_true", help="run the retrieval evaluation")
    args = ap.parse_args()

    if args.eval:
        from .eval import main as eval_main
        eval_main()
        return
    if not args.question:
        ap.error("give a question or use --eval")
    adv = Advisor(use_llm=args.llm)
    prof = Profile(country=args.country, degree_field=args.field, cgpa=args.cgpa, scale=args.scale,
                   gre_quant=args.gre_quant, gre_awa=args.gre_awa)
    res = adv.run(" ".join(args.question), prof)
    print(res.answer)
    if res.sources:
        print("\nSources:\n" + res.sources)
    print(f"\n[trace] intents={res.intents} programs={res.programs} tools={[c['tool'] for c in res.tool_calls]}")


if __name__ == "__main__":
    main()
