You are given one image of an artwork (painting, print, drawing, sculpture, photograph of an object, or book page). Describe only what
is visible, as a scene graph. Do not identify people, saints, gods or stories, and do not name the subject of the work: write
"woman", "old man", "winged figure", "infant", "lion", "book", never "the Virgin", "Saint Jerome", "angel Gabriel" or "Annunciation".

Return one JSON object and nothing else:

{"objects": [{"id": "o1", "name": "<noun phrase>", "box": [x0, y0, x1, y1], "attributes": ["...", ...]}],
 "relations": [["o1", "<predicate>", "o2"], ...]}

Objects
- "box" in thousandths of the image width (x) and height (y), 0 <= x0 < x1 <= 1000, 0 <= y0 < y1 <= 1000, origin top left; the
  box must enclose the object tightly. Look at the whole image, then at each quarter of it, so that small objects are not missed.
- Name people by visible type: man, woman, old man, old woman, young man, young woman, child, infant, winged figure, skeleton,
  crowd (a group as one object). Add age, clothing, headgear, nudity, halo, wings as attributes.
- Name every animal and every object that is held, worn or carried, or that stands out. Prefer these names when they fit: book,
  scroll, letter, key, sword, spear, lance, bow, arrow, shield, helmet, crown, wreath, halo, cross, crucifix, chalice, cup, jug,
  bowl, dish, lamp, candle, skull, hourglass, globe, scales, mirror, staff, crozier, sceptre, palm branch, lily, flower, fruit,
  wheel, anchor, tower, ladder, spade, net, basket, bag, purse, coin, musical instrument (name it), tablet, pen, inkwell, table,
  desk, chair, throne, bed, cradle, tomb, coffin, altar, curtain, window, door, column, arch, boat, cart, carriage, horse, dog,
  lion, lamb, sheep, ox, donkey, dove, eagle, peacock, fish, serpent, dragon, tree, mountain, river, sea, sky, cloud, sun, moon,
  star, building, church, city, ruins, text, inscription, coat of arms, frame, page.
- Attributes: posture (standing, seated, kneeling, lying, rising, walking, running, falling, riding, flying), gesture (raises hand,
  points, hands joined, arms open, hand on chest), gaze (looks up, looks down, looks at viewer), state (naked, dead, asleep,
  wounded, bound), clothing and colour.

Relations
- First the actions and contacts between figures and with objects, which matter most; use one of: holds, carries, wears, uses,
  writes with, reads, plays, pours, eats, drinks, nurses (breastfeeds), embraces, kisses, touches, supports, leans on, sits on,
  stands on, lies on, kneels before, bows to, prays to, blesses, crowns, gives to, receives from, offers to, shows, points at,
  gestures to, speaks to, looks at, listens to, leads, follows, pulls, pushes, rides, drives, fights, strikes, kills, pierces,
  binds, flees from, rises from, falls from, emerges from, enters, hangs on, contains, is part of.
- Use "has attribute" (o1 has attribute o2) for an object that characterises a figure without necessarily being touched (a
  lion lying at a man's feet, a wheel beside a woman, a tower behind her); use "holds" only for real contact.
- Then, only if useful, at most a few spatial relations: above, below, left of, right of, in front of, behind, inside, around.
  Left and right are those of the viewer. Never write both a relation and its inverse (not "o1 left of o2" and "o2 right of o1").
- A relation only between declared ids, only if clearly visible. If uncertain, leave it out.
