---
title: The audiobook that didn't exist
slug: the-audiobook-that-didnt-exist
description: "A book I couldn't finish, no audiobook to buy — so I spent a weekend building an app that reads EPUBs aloud."
date: 2026-06-08
updated: 2026-06-08
status: published
tags:
  - projects
  - ai
  - tts
---

> *"Phonographic books, which will speak to blind people without effort on their part."*
> — Thomas Edison, *The Phonograph and Its Future* (1878)

It had been more than a year since I started reading *The Life and Death of Democracy*, and I hadn't finished it yet. Having enjoyed the flexibility of audiobooks, I decided to buy the audiobook version instead. Unfortunately, I found that it did not exist.

That's when I imagined it would be feasible to create an application that would read EPUBs to me. Despite my background in coding, I wasn't quite willing to sacrifice the time required to write my own app by hand. The idea was shelved—until recently, when, with the improvements to LLMs, it became clear it would be feasible to create a prototype over a weekend.

So I got to work. It turned out to be a matter of writing a spec for the application using chat, which is quite capable of understanding that an audio app needs the ability to skip forward and back (it might have forgotten about the play button at some point). Building the prototype from scratch was quick, maybe two hours.

The bulk of the work turned out to be in the fine-tuning of the text-to-speech engine. An engine that both uses a local neural network and sounds natural takes a good amount of CPU. Synthesizing a medium-length sentence takes around ~7 seconds, which is not the amount of time you want to wait when you start the app.

![A skeleton sitting at a table with the caption "still waiting" — the universal mood of waiting for something slow to load](https://media1.tenor.com/m/fRcC6K4sPOYAAAAd/waiting-skeleton.gif)

So I ended up adding a buffering mechanism, cutting the first sentences into smaller pieces, tweaking, etc.

Lastly, implementing PDF was yet another story on its own. But let's leave that for another post. Here's the link, by the way: [github.com/stijn-nefkens/narrator](https://github.com/stijn-nefkens/narrator)
