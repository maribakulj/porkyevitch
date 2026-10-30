You are given one image of an artwork (painting, print, drawing, sculpture or book page). Describe only what is visible in it,
as a scene graph. Do not identify people, saints, gods or stories, and do not name the subject of the work: write "woman",
"old man", "winged figure", "child", "lion", "book", never "the Virgin", "Saint Jerome", "angel Gabriel" or "Annunciation".

Return one JSON object and nothing else:

{
  "objects": [
    {"id": "o1", "name": "<short English noun phrase>", "box": [x0, y0, x1, y1],
     "attributes": ["<visible posture, gesture, clothing, colour, state>", ...]}
  ],
  "relations": [["o1", "<short English predicate>", "o2"], ...]
}

Rules:
- "box" is in thousandths of the image width (x) and height (y): 0 <= x0 < x1 <= 1000, 0 <= y0 < y1 <= 1000, origin top left.
- List every person and animal, and every object large or salient enough to be identified; group a crowd or a set of identical
  small things as one object with a plural name ("trees", "soldiers").
- Relations only between declared ids: spatial (left of, above, behind, inside), contact (holds, wears, sits on, stands on),
  action (looks at, points at, kneels before, carries, embraces, fights) or other visible links.
- Left and right are those of the viewer of the image.
- If something is uncertain, leave it out.
