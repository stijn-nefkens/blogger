---
title: Het schild dat niets blokkeert
slug: het-schild-dat-niets-blokkeert
description: "De AI bevestigde wat we al vermoedden: de Riot shield in Sheepz blokkeert niets — en JASS blijkt geen taal waar de modellen sterk in zijn."
date: 2026-06-09
updated: 2026-06-09
status: published
tags:
  - sheepz
  - ai
  - gamedev
---

> *"Program testing can be used to show the presence of bugs, but never to show their absence."*
> — Edsger W. Dijkstra

We wisten het eigenlijk al wel, maar het werd er nog even ingewreven door de AI: de Riot shield ability in Sheepz werkt niet.

> **High — RiotShield never actually blocks anything.** The constructor calls `removeEffect()`, which calls `e.unshield()` before any `shield()` has ever run. The shield count is a counter (`hasShield() = shields > 0`). That unmatched `unshield()` permanently offsets it by −1, so while the shield is "active" the count is 0 and `hasShield()` is false. Projectiles are never deflected.

Gelukkig wist ook de AI niet alle bugs te fixen, en was het zelfs in staat een nieuwe bug te introduceren.

![Whack-a-mole: elke keer dat er één mol wordt geslagen, popt er een nieuwe op — de bug-fix-ervaring samengevat](https://media.giphy.com/media/KMhBXWpDlG8N021dxL/giphy.gif)

Helaas werken de modellen beter met programmeertalen waar ze al meer van gezien hebben. Blijkbaar staat JASS niet op deze lijst (Just Another Scripting Syntax).

Link: [hiveworkshop.com/threads/sheepz.358444](https://www.hiveworkshop.com/threads/sheepz.358444/)
