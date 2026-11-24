+++
title = "Review Layout"
description = "A product review with rating, pros and cons, and specifications."
author = "Hugo Authors"
date = "2019-03-13"
layout = "review"
tags = ["layouts", "themes"]
categories = ["themes"]
[[images]]
  src = "img/2019/03/pic03.jpg"
  alt = "Table Top View"

[review]
  product = "Example 40"
  brand = "Sample Brand"
  rating = 4.5
  price = "$399"
  verdict = "Cools fast and uses little power. The noise at night is the only thing we would change."
  pros = ["Reaches temperature in under an hour", "Low power draw", "Reversible lid"]
  cons = ["The compressor can be heard at night", "Heavier than a thermoelectric cooler"]
  disclosure = "Made-up product. In a real review, say here whether the link is an affiliate link."
  [[review.specs]]
    name = "Capacity"
    value = "40 litres"
  [[review.specs]]
    name = "Power"
    value = "12 V, 24 V and 230 V"
  [[review.specs]]
    name = "Weight"
    value = "15 kg"
  [[review.links]]
    label = "See it at the shop"
    url = "https://example.org/"
+++

This post uses `layout = "review"`. The product box, the pros and cons, the
specifications and the links come from the `review` table in the front matter.
The text of the review is the body of the post, as usual.

## How we used it

Four weekends and a full week, always running from the house battery.

## Cooling and power

Full and with warm weather outside, it kept its temperature without trouble.

## Noise

Unnoticeable by day. At night, in a quiet van, you hear the compressor start.

## Who it is for

Anyone who goes out often and wants to stop depending on ice.
