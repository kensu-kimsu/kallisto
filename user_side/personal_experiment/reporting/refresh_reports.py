from user_side.personal_experiment.reporting.performance_tracker import generate_report
from user_side.personal_experiment.reporting.periodic_reports import generate_periodic_reports


def main():
    print("========================================")
    print("PERSONAL LLM TRADING REPORT REFRESH")
    print("========================================")
    print()

    print("Step 1: Updating cumulative performance charts...")
    generate_report()

    print()
    print("Step 2: Updating daily / weekly / monthly reports...")
    generate_periodic_reports()

    print()
    print("========================================")
    print("REPORT REFRESH COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()
