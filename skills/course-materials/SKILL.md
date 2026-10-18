---
name: course-materials
description: How {{GROUP}} builds course materials — alignment to objectives, file layout, versions for students vs. instructor, and release checks. Use for any lecture, assignment, lab, quiz or syllabus work.
---

# Course materials

Layout (under `{{STATE}}/deliverables/`):
- `course/` — plan.md (week-by-week), syllabus.md, faq.md
- `lectures/week-NN/` — outline.md, slides .pptx, notes, activity
- `assessments/<name>/` — student version; `solutions/` kept separate
- `labs/<name>/` — notebooks/code; starter vs. solution separated
- `lms/` — copy-ready page text, calendars, announcement drafts

Rules:
1. Start from the learning objectives (course profile / handbook). Every
   item says which objective it serves.
2. Outline first, then build: a 5–10 line outline goes to the instructor (or
   course manager) before full materials.
3. Student-facing files never contain solutions, answer keys, grading notes
   or instructor comments. Check before saving.
4. Dates: copy them from the course plan, with time zone. Never guess.
5. Code and data must run from a clean environment; list requirements.
6. Before release: accessibility check (alt text, headings, captions,
   contrast) and a reviewer pass. Note both in the item's README.
7. Reuse is fine; copying others' copyrighted material wholesale is not —
   cite and link, or ask the instructor.
