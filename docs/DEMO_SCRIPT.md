# 90-second demo script

Text input only. Run against the live URL, not the local preview: the preview shows demo data, and the banner «نسخة تجريبية للتطوير» means the check is not connected.

Every question below is typed by the presenter. The example chips stay empty until the owner approves their texts, so nothing is pre-filled.

## Before recording

- Open the live URL and confirm the preview banner is gone (the check service answers).
- Confirm the composer shows the privacy line «يُرسل نصك إلى مزوّد ذكاء اصطناعي، ولا نحفظه في خوادمنا.»
- Run each question once beforehand with Nami's `X-Request-ID` log at hand. Record the result state for each. Do not record the video until each beat shows the expected state.
- Beat 2 needs the hadith connector (V3). The personal-case question is the owner-approved Level D example below. If either result is not live, drop that beat instead of replacing it with a mock card.

## Script

| Time | On screen | Say (in short) | Expected state |
|---|---|---|---|
| 0:00–0:10 | Input screen. Heading «ما الذي تريد التحقق منه؟», the AI notice, and the privacy line under the composer. | Tabayyan checks a religious claim or question against approved sources. It is an AI tool, not a fatwa. The text is sent to an AI provider, and we do not store it on our servers. | Notice visible before any submit. |
| 0:10–0:25 | Type «من هو خاتم الأنبياء؟» and press «إرسال». Show the loading text «جارٍ التحقق من الادعاءات… يرجى الانتظار». | Ask one question. The check runs against the approved sources. | Loading state, then results. |
| 0:25–0:40 | **Beat 1, verse.** The card with the state badge «يؤيده المصدر المعتمد», the block «نص من المصدر» with its exact reference (Quran 33:40), and the source link «المصدر». | The verse is shown as it appears in the source, with its reference. The explanation below it is labelled as generated. | SUPPORTED, verse text copied from the source record. |
| 0:40–0:55 | **Beat 2, hadith.** Type «هل الابتسامة في وجه أخي صدقة؟» Show the card: the badge, the source text block, the grade under «الحكم», and the source link. | A hadith appears only with its source and its grade, and the grade is copied from the source. | SUPPORTED, hadith with grade and link. |
| 0:55–1:10 | **Beat 3, referral.** Type «أنا في بلد غير مسلم، هل يجوز لي أن أعقد زواجي في المحكمة المدنية فقط؟». Show the card with «جهة مرجعية للفتوى» and «سؤال جاهز للطرح». | A personal ruling is outside what the tool answers. It gives general information and points to an official body, with a question ready to ask. | Level D: general information and referral, no ruling. |
| 1:10–1:20 | Open «كيف تتحقق بنفسك؟» on the referral card (or beat 1 card). | Every card ends with two lines on how to check it yourself. | Collapsible block opens. |
| 1:20–1:30 | Scroll back to the top. Show the notice «هذه أداة ذكاء اصطناعي، وليست فتوى.» | Close on the notice: AI tool, not a fatwa. | Notice visible. |

## Open items before recording

- **Referral question (beat 3):** «أنا في بلد غير مسلم، هل يجوز لي أن أعقد زواجي في المحكمة المدنية فقط؟» is the owner-approved Level D demo question. Confirm that the live response gives general information and a referral, with no ruling.
- **Hadith beat (beat 2):** depends on the hadith connector. Check the card's grade and link against the record before recording.
- **Verse beat (beat 1):** the question and the 33:40 reference come from the owner's acceptance list. Confirm the live state with Nami before recording.

## Do not

- Do not show a card from the local preview or from mock data as if it were live.
- Do not read the explanation as scripture. Say that the explanation is generated, and that the quoted text comes from the source.
- Do not claim accuracy numbers, speed or coverage in the narration. Use only results that Nami has recorded.
