# Prompts

These are my real prompts, in the order I sent them, on Nov 3 and Nov 4 2026. Times are Central. Clip numbers point to the screen recordings behind the video, and 3 of the prompts weren't recorded.

I didn't reword anything, so the typos and dictation stayed in. I only replaced personal details and the products we really bought, and each replacement is in square brackets, like `[my wife]`, `[product]` or `[Walmart product id]`.

What isn't here. The order-history collectors and the suggester came from separate sessions in October, and those prompts aren't in this file. Neither is the prompt stored in the scheduled task, or my answers to Claude's pop-up questions.

## Start with what good looks like

I didn't start with a tool. I asked for acceptance criteria first, tool-neutral and pass/fail, so any solution could be judged the same way. `/goal-builder` is my skill that interviews me and then writes a `/goal` prompt, and `/goal` is that finished prompt being run.

**Nov 3 5:56 a.m.** (Clip 01)

```text
/goal-builder Every week, my wife manages grocery shopping across multiple stores. Throughout the week, she must constantly remember and manually add items to her list, creating ongoing mental load and extra planning time. Can you help me come up with a list of acceptance criteria for a solution?
```

**Nov 3 6:19 a.m.** (Clip 04)

```text
/goal Write acceptance criteria for a solution that cuts [my wife]'s weekly grocery mental load. Don't build anything. First read ~/Documents/goal-builder/grocery-agent/map.md, GLOSSARY.md beside it (use its terms, like Capture, Usual store, Forgotten item), and ~/grocery-agent/attempts.md and findings.md.

Keep it tool-neutral. [my wife] is the main user. Group the criteria as Must, Should, Could. Each one must be pass/fail testable. Cover remembering what's due (suggestions), Capture in seconds by Siri, her Notes/Reminders list, or straight in Instacart, routing to the Usual store with a tap to move it, and one-tap approval from her before anything enters a cart. Stores are ALDI, Costco and Walmart. Targets are under 10 min a week of her planning and at most 1 Forgotten item a week with zero extra trips, over 4 straight weeks. Her cart items are never changed or removed. Out of scope are checkout, meal planning and price comparison.

Invoke the docs skill and put it in a Claude Doc. Track steps in the task list and keep a short attempt log.

Then update the map. Redraw the Destination around less remembering and adding for [my wife]. Add the doc link to Notes and record today's decisions. Add meal planning and price comparison to Out of scope. Bump the index Last touched and add keywords (acceptance criteria, mental load, capture, Siri). Log the result under Goals written. Done when the doc exists, every criterion is testable and the map is updated.
```

## Compare four free options

Same criteria, four solutions, all using tools we already have. The pick was a grocery agent on the Mac, built on the shopping list we already keep.

**Nov 3 6:25 a.m.** (Clip 05)

```text
/goal-builder give me 4 solutions to this problem utilizing the acceptance criteria
```

**Nov 3 6:30 a.m.** (Clip 05)

```text
/goal Compare 4 solutions to [my wife]'s grocery mental load against our acceptance criteria. Don't build anything. First read ~/Documents/goal-builder/grocery-agent/map.md, GLOSSARY.md beside it (use its terms), ~/grocery-agent/attempts.md, and the criteria doc [criteria doc link].

All 4 must be free and use only tools we already have. Siri, our iPhones, Reminders/Shortcuts, Instacart, the Walmart app, Claude on both phones, the Mac grocery agent. No new apps. The 4 are Apple-only (shared Reminders, Siri, Shortcuts), Instacart/Walmart-only (add straight to carts), the grocery agent reading Reminders and filling carts after her tap, and Claude-centered (she talks to Claude, which keeps the list and runs the weekly fill).

Grade each one pass, partial or fail on every M, S and C criterion, with the evidence for each mark. Add setup hours and the weekly steps for her and for me. Use official docs and quick read-only checks. No installs, sign-ups or cart changes. For the store sites use only Claude in Chrome. Mark anything you couldn't verify as unverified. Rank all 4 by Musts passed, then Shoulds, then effort, and pick one with the reason.

Invoke the docs skill and put it in a new tab in that doc. Track steps in the task list and log attempts in attempts.md.

Then update the map. Tick the "which option" question with the pick. Record new questions and gaps. Bump the index Last touched. Log the result under Goals written.
```

**Nov 3 6:33 a.m.** (not recorded)

```text
I already have a shopping list by the way
```

**Nov 3 6:40 a.m.** (not recorded)

```text
Yes, write it
```

## First build, and it was wrong

Look closely at this prompt. It asks for a new weekly list, an approval item and a Mac wake step. Those were my ideas, and all three turned out wrong.

**Nov 3 6:49 a.m.** (Clip 06)

```text
/goal Build the weekly grocery run for [my wife]. First read ~/Documents/goal-builder/grocery-agent/map.md, GLOSSARY.md (use its terms), the criteria doc [criteria doc link] and every entry in ~/grocery-agent/attempts.md.

Run it as Claude desktop scheduled tasks on this Mac. The first runs Thursdays at 7 a.m. It reads the Reminders Shopping list plus order history and writes a Weekly list in Reminders with ALDI, Costco and Walmart sections and one Approve item. Use the Usual store, and flag new items. A second task checks every 15 min until noon. If Approve isn't checked by noon, add nothing.

After Approval, fill ALDI and Costco with the Instacart connector, or Claude in Chrome if it fails on Family Carts. Fill Walmart via Chrome (invoke the chrome-browser skill). Only add. Skip what's in a cart, never remove or check out. The first run adds just 1 item per store and tells me which ones to remove.

For my steps (connect Instacart in Claude, wake the Mac before 7 Thursday), build a guided script from ~/.claude/skills/goal-builder/references/setup-script-template.sh. Never handle my passwords.

Track steps in the task list and log attempts. Snapshot carts before and after. Test with a dry run first. Done when the 1-item adds land and carts are otherwise unchanged, else report the blocker. Update the map and Goals written, and bump the index.
```

## Correct the design

Reading the result, I saw the design was wrong for how we really live. It made new lists, woke a Mac that's always on, and made my wife check things twice. These prompts cut it down to one shared list and two steps, and they're where "we should just be able to say butter" came from.

**Nov 4 2:42 p.m.** (Clip 07)

```text
1. This shouldn't be working. Creating a new list in Reminders will create a lot of new lists and will require cleanup. We should all be working off of one shared list. The shared list that we already have set up with [my wife] in our household is the list you should be working from, and you shouldn't be creating new lists to work off of.
   2. The Mac is already awake. I keep it online 24/7, so there's no need to wake it. I have it plugged in and on 24/7.
      3. I need more clarification around where you're saying the shortfalls are in terms of store sections, and then more understanding around the guided script of what it's supposed to do. Ideally, I don't need to tell you which store to buy from for each item. You should be able to look at the history in Instacart or Walmart to figure out what item I'm talking about and then update it correctly. The idea is to have us be off hands as much as possible, so we should just be able to say "butter" and you take it from there.
         4. Just give me a general, high-level overview of how this works, TL;DR style, skimmable.
```

**Nov 4 2:53 p.m.** (Clip 08)

```text
So, quick note is that she shouldn't be checking off anything in the list itself. [my wife] will only be involved in two steps:

1. When she's adding things to the shopping list. That actually is the step that every family member is a part of. We all add things to the shopping list.
2. Once on Thursday morning, after you've put everything in the cart, she'll check the cart itself. That will be where she adds new items or takes items off, and that way she doesn't have to do it twice or double-check things twice.
```

**Nov 4 2:57 p.m.** (Clip 09)

```text
Yes, update the criteria doc, but my other question is: how are you determining what items are due outside of what's on the shopping list? This short, skimmable answer
```

**Nov 4 3:01 p.m.** (Clip 09)

```text
Okay, this was good. What are the next steps?
```

## First full run, and the wrong items

The first full run put 3 wrong items in the cart. Its grade was 7 held, 2 failed and 6 not proven. So I asked for a reset, a retry, and a new step where it checks its own work before anyone reviews. The cart reset also removed items my family had added, which comes back at the end of this file.

**Nov 4 3:02 p.m.** (Clip 09)

```text
Well, we need to do a test run and a beta test of this.

1. Is there anything I need to do in Claude to make sure that this is run? I know you said that we needed to run the task once in Claude Desktop in the morning. Is that the beta test?
2. I want to do a full run now, a day early, just to make sure that I can see the output there and see the computer run through this.
```

**Nov 4 3:22 p.m.** (Clip 11)

```text
does this build align with our acceptance criteria? give me a tldr answer that's skimmable
```

**Nov 4 3:30 p.m.** (Clip 11)

```text
Everything:

1. Delete the carts.
2. Don't delete the open order that we have in ALDI because that one was sent on purpose.
3. The carts that we messed with or that we added, we need to remove them and then empty them for Walmart and for ALDI.
4. Try again after we fix the wrong item bug.
5. Explain suggestions one more time.
```

**Nov 4 3:34 p.m.** (Clip 12)

```text
Can we add a step to the process so that, after it adds things to the cart and double-checks if there's anything wrong, it removes it before sending it for review to me
```

## Fix the bug properly

The retry still picked 2 wrong sizes. This time I used a Goal Builder round and made it reproduce the bug first. The cause was that the add script compared only the first 40 characters of a product name. The fix clicks only a button with the full name, and otherwise it clicks nothing.

**Nov 4 3:53 p.m.** (Clip 14)

```text
/goal-builder yes fix it.
```

**Nov 4 3:55 p.m.** (Clip 14)

```text
1. A. How should the fix be tested, given the carts are shared and full right now? The ticket was to reproduce the bug on saved copies of the [product] and [product] pages, which is the case where it failed, then run a no-click check on. That makes sense. We can do that.
2. We can do A.
3. How far should the fix go? Fix the added regression test and tighten run block. I agree with that as well, so A as well.

 For number 3
```

**Nov 4 3:56 p.m.** (Clip 14)

```text
Yes, write the goal
```

**Nov 4 3:57 p.m.** (Clip 15)

```text
/goal Fix ~/grocery-agent/collectors/add_walmart.js before Thursday 7 a.m. It compares only 40 characters of the name, so [product] and [product] pages clicked a recommended size. First read RUNBOOK.md, attempts.md, and GLOSSARY.md and map.md in ~/Documents/goal-builder/grocery-agent/, and use the glossary's terms.

Reproduce first. Save the [product] ([Walmart product id]) and [product] ([Walmart product id]) walmart.com/ip pages as test copies with only the title and button labels, no account data, and show the old script picking the wrong size. Post 3-5 ranked guesses with disproving predictions, then continue. Change one thing at a time. Tag debug logs and remove them.

The script may click only a button labeled "Add to cart - " plus the full page title. Duplicates of that label are fine. No match means no click and a refusal. Add a regression test that fails on the old script and passes on the new. Change RUNBOOK step 7 so each add compares full name and size to the cart line.

Invoke chrome-browser, Claude in Chrome only. Run a no-click check on [10 Walmart product ids]. Never click Add or change a cart. Leave Instacart alone. If a page refuses, report it, don't loosen the match.

Track steps in the task list and log attempts in attempts.md. No repeat tweaks without new evidence. Report unverified checks. When done, update the map and the index's Last touched, add the result to Goals written, and say which guess was right.
```

## Test it like the real thing

Empty carts, then a run started the way the scheduled run starts.

**Nov 4 4:08 p.m.** (Clip 16)

```text
can we do one more test? empty carts for walmart, aldi and costco and do a full end to end test.
```

**Nov 4 4:08 p.m.** (Clip 16)

```text
to be clear lets run this as if it were a real test, like a scheduled run
```

**Nov 4 4:09 p.m.** (Clip 16)

```text
to be clear start this in a new chat like you did before
```

## Question the output

I stopped asking it to build and started asking it to explain itself. The grade on this run was 4 held, 0 failed and 11 not proven, out of 15 Musts. Most of the unproven ones need real weeks of use.

**Nov 4 4:40 p.m.** (Clip 18)

```text
why did you add [product]?
```

**Nov 4 4:41 p.m.** (Clip 18)

```text
why is aldi so low?
```

**Nov 4 4:43 p.m.** (Clip 18)

```text
what did you suggest for walmart?
```

**Nov 4 4:44 p.m.** (Clip 18)

```text
are you limited to just 3 suggestions?
```

**Nov 4 4:45 p.m.** (Clip 18)

```text
can you judge the last run against the criteria and see if we met it?
```

**Nov 4 4:55 p.m.** (Clip 19)

```text
For the [product], do we normally buy them from Walmart or from ALDI? I know the last purchase was from ALDI, but do we normally get them from Walmart?
```

## Clean up my mess

Asking it to put the family's items back after the earlier cart reset, so the real run could start clean.

**Nov 4 5:12 p.m.** (not recorded)

```text
okay can you return our cart back to the state it was before we started working? i think you said that some items were accidentally deleted that [my wife] had already added? that way the run can run clean tomorrow. and also add the items back to the shopping list as well that you took off if you took a state of that.
```
