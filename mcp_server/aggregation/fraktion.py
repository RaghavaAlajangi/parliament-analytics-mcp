"""Pure functions for Fraktion distribution aggregation."""

from collections import Counter

from mcp_server.dip.models import Person
from mcp_server.schemas.tool_outputs import FraktionDistribution, FraktionShare

FRAKTIONSLOS = "Fraktionslos"


def compute_distribution(
    persons: list[Person],
    wahlperiode: int | None = None,
) -> FraktionDistribution:
    """Compute Fraktion percentage distribution from a list of Person records.

    Politicians with no Fraktion are counted under 'Fraktionslos'.
    Data quality issues are surfaced in data_quality_notes, never silently
    dropped.

    Parameters
    ----------
    persons : list[Person]
        Person records to aggregate.
    wahlperiode : int
        Wahlperiode number embedded in the returned result.

    Returns
    -------
    FraktionDistribution
        Sorted distribution with percentage shares and data quality notes.
    """
    counts: Counter[str] = Counter()
    missing = 0

    for person in persons:
        fraktion = (
            person.fraktion_for(wahlperiode)
            if wahlperiode is not None
            else person.fraktion
        )
        if fraktion:
            counts[fraktion] += 1
        else:
            counts[FRAKTIONSLOS] += 1
            missing += 1

    total = sum(counts.values())
    notes: list[str] = []

    if missing:
        notes.append(
            f"{missing} of {total} records had no Fraktion assigned (counted "
            f"as '{FRAKTIONSLOS}')."
        )

    if total == 0:
        return FraktionDistribution(
            wahlperiode=wahlperiode or 0,
            total_politicians=0,
            shares=[],
            data_quality_notes=["No politician records found."],
        )

    shares = [
        FraktionShare(
            fraktion=fraktion,
            count=count,
            percentage=round(count / total * 100, 2),
        )
        for fraktion, count in counts.most_common()
    ]

    return FraktionDistribution(
        wahlperiode=wahlperiode or 0,
        total_politicians=total,
        shares=shares,
        data_quality_notes=notes,
    )
