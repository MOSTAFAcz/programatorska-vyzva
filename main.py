import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
CSV_FILE = "dochazka.csv"
STANDARD_START = datetime.strptime("08:00", "%H:%M").time()
STANDARD_END = datetime.strptime("17:00", "%H:%M").time()


def nacti_data(nazev_souboru=CSV_FILE):
    """Načte záznamy docházky z CSV souboru."""
    data = []

    with open(nazev_souboru, "r", encoding="utf-8-sig", newline="") as soubor:
        reader = csv.DictReader(soubor, delimiter=";")

        for radek in reader:
            if not radek or not radek.get("zaměstnanec"):
                continue

            zaznam = {
                "číslo čipu": radek["číslo čipu"].strip(),
                "zaměstnanec": radek["zaměstnanec"].strip(),
                "příchod": datetime.strptime(radek["příchod"].strip(), "%Y-%m-%d %H:%M"),
                "odchod": datetime.strptime(radek["odchod"].strip(), "%Y-%m-%d %H:%M"),
            }
            data.append(zaznam)

    return data


def calculate_employee_summary(records):
    """Sestaví přehled práce zaměstnanců za celé období."""
    grouped = defaultdict(list)
    for record in records:
        grouped[record["zaměstnanec"]].append(record)

    result = []
    for employee, entries in sorted(grouped.items()):
        total_minutes = 0
        late_minutes = 0
        overtime_minutes = 0

        for entry in entries:
            duration = entry["odchod"] - entry["příchod"]
            total_minutes += int(duration.total_seconds() // 60)

            start_time = entry["příchod"].time()
            end_time = entry["odchod"].time()

            if start_time > STANDARD_START:
                late_minutes += int((datetime.combine(entry["příchod"].date(), start_time) - datetime.combine(entry["příchod"].date(), STANDARD_START)).total_seconds() // 60)

            if end_time > STANDARD_END:
                overtime_minutes += int((datetime.combine(entry["odchod"].date(), end_time) - datetime.combine(entry["odchod"].date(), STANDARD_END)).total_seconds() // 60)

        prace_hodin = total_minutes / 60
        prumer_hodin = prace_hodin / len(entries)

        result.append(
            {
                "zaměstnanec": employee,
                "dny": len(entries),
                "práce_hodin": round(prace_hodin, 2),
                "průměrně_hodin": round(prumer_hodin, 2),
                "zpoždění_minut": late_minutes,
                "přesčas_minut": overtime_minutes,
            }
        )

    return sorted(result, key=lambda item: (-item["práce_hodin"], item["zpoždění_minut"]))


def calculate_daily_summary(records):
    """Seskupuje denní výkon dle data."""
    grouped = defaultdict(list)
    for record in records:
        grouped[record["příchod"].date()].append(record)

    result = []
    for datum, entries in sorted(grouped.items()):
        total_minutes = 0
        late_minutes = 0
        for entry in entries:
            total_minutes += int((entry["odchod"] - entry["příchod"]).total_seconds() // 60)
            if entry["příchod"].time() > STANDARD_START:
                late_minutes += int((datetime.combine(entry["příchod"].date(), entry["příchod"].time()) - datetime.combine(entry["příchod"].date(), STANDARD_START)).total_seconds() // 60)

        result.append(
            {
                "datum": datum.strftime("%Y-%m-%d"),
                "zaměstnanců": len(entries),
                "celkem_hodin": round(total_minutes / 60, 2),
                "zpoždění_minut": late_minutes,
            }
        )

    return result


def calculate_late_leaders(records, limit=5):
    """Vrátí zaměstnance s největším součtem zpoždění."""
    summary = calculate_employee_summary(records)
    return sorted(summary, key=lambda item: (-item["zpoždění_minut"], item["zaměstnanec"]))[:limit]


def calculate_top_productivity(records, limit=5):
    """Vrátí zaměstnance s nejvyšším průměrným výkonem."""
    summary = calculate_employee_summary(records)
    return sorted(summary, key=lambda item: (-item["průměrně_hodin"], -item["přesčas_minut"], item["zaměstnanec"]))[:limit]


def find_employee_records(records, jmeno):
    """Vyhledá všechny záznamy jednoho zaměstnance."""
    return [entry for entry in records if entry["zaměstnanec"].lower() == jmeno.lower()]


def render_table(columns, rows, title):
    table = Table(title=title, show_lines=True)
    for column in columns:
        table.add_column(column, overflow="fold")
    for row in rows:
        table.add_row(*row)
    console.print(table)


def print_management_summary(records):
    employee_summary = calculate_employee_summary(records)
    daily_summary = calculate_daily_summary(records)
    top_late = calculate_late_leaders(records)
    top_productive = calculate_top_productivity(records)

    if employee_summary:
        total_hours = sum(item["práce_hodin"] for item in employee_summary)
        avg_day = total_hours / len(daily_summary) if daily_summary else 0
        busiest_day = max(daily_summary, key=lambda item: item["celkem_hodin"], default={"datum": "-"})
        least_busy_day = min(daily_summary, key=lambda item: item["celkem_hodin"], default={"datum": "-"})

        console.print(
            Panel.fit(
                f"[bold]Celkový součet prac. hodin:[/bold] {total_hours:.2f} h\n"
                f"[bold]Průměr za den:[/bold] {avg_day:.2f} h\n"
                f"[bold]Nejvíce pracující den:[/bold] {busiest_day.get('datum', '-')} ({busiest_day.get('celkem_hodin', 0):.2f} h)\n"
                f"[bold]Nejklidnější den:[/bold] {least_busy_day.get('datum', '-')} ({least_busy_day.get('celkem_hodin', 0):.2f} h)\n"
                f"[bold]Největší zpoždění:[/bold] {top_late[0]['zaměstnanec']} ({top_late[0]['zpoždění_minut']} min)\n"
                f"[bold]Nejproduktivnější:[/bold] {top_productive[0]['zaměstnanec']} ({top_productive[0]['průměrně_hodin']:.2f} h/den)",
                title="Shrnutí pro vedení",
            )
        )


def export_report(records, type_report):
    """Uloží zvolený přehled do CSV."""
    target_dir = Path("exports")
    target_dir.mkdir(exist_ok=True)

    if type_report == "employee":
        rows = calculate_employee_summary(records)
        fieldnames = ["zaměstnanec", "dny", "práce_hodin", "průměrně_hodin", "zpoždění_minut", "přesčas_minut"]
    elif type_report == "daily":
        rows = calculate_daily_summary(records)
        fieldnames = ["datum", "zaměstnanců", "celkem_hodin", "zpoždění_minut"]
    else:
        raise ValueError("Neznámý typ exportu")

    filename = target_dir / f"{type_report}_report.csv"
    with open(filename, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    console.print(f"[green]Export uložen do:[/green] {filename}")


def print_employee_detail(records):
    name = input("Zadejte jméno zaměstnance: ").strip()
    matches = find_employee_records(records, name)

    if not matches:
        console.print("[red]Zaměstnanec nebyl nalezen.[/red]")
        return

    rows = []
    for entry in matches:
        duration_min = int((entry["odchod"] - entry["příchod"]).total_seconds() // 60)
        delay_min = max(
            0,
            int((entry["příchod"] - datetime.combine(entry["příchod"].date(), datetime.strptime("08:00", "%H:%M").time())).total_seconds() // 60),
        )
        overtime_min = max(
            0,
            int((entry["odchod"] - datetime.combine(entry["odchod"].date(), datetime.strptime("17:00", "%H:%M").time())).total_seconds() // 60),
        )
        rows.append(
            [
                entry["příchod"].strftime("%Y-%m-%d"),
                entry["příchod"].strftime("%H:%M"),
                entry["odchod"].strftime("%H:%M"),
                f"{duration_min/60:.2f} h",
                f"{delay_min} min",
                f"{overtime_min} min",
            ]
        )

    render_table(["Datum", "Příchod", "Odchod", "Délka", "Zpoždění", "Přesčas"], rows, f"Detailní docházka: {name}")


def menu():
    records = nacti_data()

    while True:
        console.print(
            Panel.fit(
                "[bold cyan]Manažerský přehled docházky[/bold cyan]\n\n"
                "[1] Přehled zaměstnanců\n"
                "[2] Denní přehled\n"
                "[3] Největší zpoždění\n"
                "[4] Nejproduktivnější zaměstnanci\n"
                "[5] Detail zaměstnance\n"
                "[6] Export reportu do CSV\n"
                "[0] Ukončit\n",
                title="Hlavní menu",
            )
        )

        volba = input("Vyberte možnost: ").strip()

        if volba == "1":
            summary = calculate_employee_summary(records)
            render_table(
                ["Zaměstnanec", "Dny", "Celkem h", "Průměr h/den", "Zpoždění", "Přesčas"],
                [
                    [
                        item["zaměstnanec"],
                        str(item["dny"]),
                        f"{item['práce_hodin']:.2f}",
                        f"{item['průměrně_hodin']:.2f}",
                        f"{item['zpoždění_minut']} min",
                        f"{item['přesčas_minut']} min",
                    ]
                    for item in summary
                ],
                "Přehled zaměstnanců",
            )
            print_management_summary(records)

        elif volba == "2":
            summary = calculate_daily_summary(records)
            render_table(
                ["Datum", "Počet zaměstnanců", "Celkem hodin", "Zpoždění"],
                [
                    [item["datum"], str(item["zaměstnanců"]), f"{item['celkem_hodin']:.2f}", f"{item['zpoždění_minut']} min"]
                    for item in summary
                ],
                "Denní přehled",
            )

        elif volba == "3":
            leaders = calculate_late_leaders(records)
            render_table(
                ["Zaměstnanec", "Zpoždění min", "Průměr h/den"],
                [
                    [item["zaměstnanec"], str(item["zpoždění_minut"]), f"{item['průměrně_hodin']:.2f}"]
                    for item in leaders
                ],
                "Největší zpoždění",
            )

        elif volba == "4":
            leaders = calculate_top_productivity(records)
            render_table(
                ["Zaměstnanec", "Průměr h/den", "Zpoždění min", "Přesčas min"],
                [
                    [item["zaměstnanec"], f"{item['průměrně_hodin']:.2f}", str(item["zpoždění_minut"]), str(item["přesčas_minut"])]
                    for item in leaders
                ],
                "Nejproduktivnější zaměstnanci",
            )

        elif volba == "5":
            print_employee_detail(records)

        elif volba == "6":
            export_type = input("Zvolte report [employee/daily]: ").strip().lower()
            if export_type in {"employee", "daily"}:
                export_report(records, export_type)
            else:
                console.print("[red]Neplatný typ reportu.[/red]")

        elif volba == "0":
            console.print("[green]Ukončuji aplikaci.[/green]")
            break

        else:
            console.print("[red]Neplatná volba.[/red]")

        input("\nStiskněte Enter pro návrat do menu...")


if __name__ == "__main__":
    menu()
