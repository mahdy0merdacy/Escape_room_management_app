"""Seed the local database with test rooms, objectives, hints, and clues."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from erm import database

database.init_db()

# ── Room 1: Stranger Things ──────────────────────────────────────────────────
r1 = database.create_room("Stranger Things", duration_seconds=3600)

o1 = database.add_objective(r1, "Find the hidden radio in the basement")
database.add_hint(o1, "Check behind the old washing machine.")
database.add_hint(o1, "The radio is wrapped in a red cloth.")

o2 = database.add_objective(r1, "Decode the blinking lights message")
database.add_hint(o2, "Map each light to a letter of the alphabet.")
database.add_hint(o2, "The message repeats twice — watch carefully.")

o3 = database.add_objective(r1, "Open the locked lab door")
database.add_hint(o3, "The code is on the sticky note hidden in the vent.")
database.add_hint(o3, "Code hint: it's a 4-digit year.")

database.add_clue(r1, "Walkie-talkie frequency written on the wall")
database.add_clue(r1, "Calendar with a circled date")
database.add_clue(r1, "Map of Hawkins with red X marks")

# ── Room 2: Annabelle ───────────────────────────────────────────────────────
r2 = database.create_room("Annabelle", duration_seconds=2700)

o4 = database.add_objective(r2, "Find the missing doll piece")
database.add_hint(o4, "Look inside the music box on the shelf.")
database.add_hint(o4, "The piece is sewn into the doll's dress lining.")

o5 = database.add_objective(r2, "Solve the ritual symbol puzzle")
database.add_hint(o5, "The symbols match the ones in the open book on the table.")
database.add_hint(o5, "Arrange them in the order shown in the painting.")

o6 = database.add_objective(r2, "Escape through the sealed door")
database.add_hint(o6, "The key is tied to the rocking chair's leg.")
database.add_hint(o6, "You need both the key AND the password — check the mirror.")

database.add_clue(r2, "Old photograph with a name scratched out")
database.add_clue(r2, "Candles arranged in a pentagram shape")
database.add_clue(r2, "Torn page with Latin text")

# ── Room 3: The Matrix ───────────────────────────────────────────────────────
r3 = database.create_room("The Matrix", duration_seconds=4500)

o7 = database.add_objective(r3, "Hack the terminal to get the access code")
database.add_hint(o7, "The password is hidden in the binary sequence on the wall.")
database.add_hint(o7, "Convert the binary to ASCII — it spells something.")

o8 = database.add_objective(r3, "Choose the correct pill")
database.add_hint(o8, "Read the labels carefully — one says 'reality', one says 'illusion'.")
database.add_hint(o8, "The answer is on the underside of the table.")

o9 = database.add_objective(r3, "Reach the exit door before time runs out")
database.add_hint(o9, "The door code is the last 4 digits of the phone number on the wall.")
database.add_hint(o9, "Don't forget to flip the breaker switch first.")

database.add_clue(r3, "Green code raining on the monitor")
database.add_clue(r3, "Phone with a blinking message light")
database.add_clue(r3, "Blueprint of the room layout")

print("Seeded 3 rooms: Stranger Things, Annabelle, The Matrix")
print("Each has 3 objectives with 2 hints each, and 3 clues.")
