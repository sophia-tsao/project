"""Prune topics that are no longer in the seed, and purge them from cached decks.

Topics were removed from the seed over time (untypeable answers — matrices,
complex roots, symbolic roots — or generators dropped from the library), but the
removal only stopped *new* Topic rows from being created. Existing rows lived on:
still selectable in old data, still referenced by `UserTopicSelection`, and still
frozen inside `DailyDeck.problems` JSON. A cached deck therefore kept serving an
untypeable card (a matrix the student can't type, a `\\frac{...}{...}` root), and
a user whose only selections were removed topics saw cards while the Courses page
showed nothing checked.

This migration makes the seed authoritative: any Topic whose `generator_name`
isn't in the current seed's `TOPICS` is deleted (its selections/reviews/grades
cascade away), and every cached deck has those topics' cards stripped out, with
`current_index` shifted back by however many removed cards sat before it so the
student stays on the same *remaining* card.

Reverse is a no-op: re-seeding (`manage.py seed_topics`) recreates any topic that
belongs, so we don't attempt to resurrect deleted rows or deck cards.
"""
from django.db import migrations


def prune_orphaned_topics(apps, schema_editor):
    Topic = apps.get_model("myapp", "Topic")
    DailyDeck = apps.get_model("myapp", "DailyDeck")

    # Import the seed list lazily; it's the single source of truth for which
    # generator_names are valid. (Safe here — it only reads a module-level list.)
    from myapp.management.commands.seed_topics import TOPICS

    valid_names = {gen for _name, gen in TOPICS if gen is not None}

    orphaned = Topic.objects.exclude(generator_name__isnull=True).exclude(
        generator_name__in=valid_names
    )
    orphaned_ids = set(orphaned.values_list("id", flat=True))
    if not orphaned_ids:
        return

    # Strip orphaned cards out of every cached deck, keeping the student on the
    # same remaining card by shifting current_index past any removed cards that
    # sat before it.
    for deck in DailyDeck.objects.all():
        problems = deck.problems or []
        kept = []
        removed_before_cursor = 0
        for i, problem in enumerate(problems):
            if problem.get("topic_id") in orphaned_ids:
                if i < deck.current_index:
                    removed_before_cursor += 1
                continue
            kept.append(problem)
        if len(kept) == len(problems):
            continue  # this deck had no orphaned cards
        deck.problems = kept
        deck.current_index = max(0, deck.current_index - removed_before_cursor)
        deck.save(update_fields=["problems", "current_index"])

    # Delete the Topic rows. FK cascades remove UserTopicSelection, TopicReview,
    # and DailyTopicGrade rows that pointed at them.
    orphaned.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0009_dailytopicgrade"),
    ]

    operations = [
        migrations.RunPython(prune_orphaned_topics, migrations.RunPython.noop),
    ]
