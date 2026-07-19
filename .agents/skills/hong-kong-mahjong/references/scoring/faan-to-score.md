# Converting Faan to Score

Faan is converted score in an exponential manner (i.e., each additional faan is worth more than the last). When gambling with mahjong, these scores represent money, e.g., 8 points is 8 Hong Kong dollars.

### Faan-to-score table

In typical Hong Kong mahjong (also known as Hong Kong New Style), there are two common ways to translate faan: "full spicy" and "half spicy". Players can also forgo both and agree on a custom table.

#### Full spicy

In "full spicy", the points awarded for a hand are 2 to the power of the number of faan, i.e., $2^{\text{faan}}$.

| Faan | Points | Formula                           |
|------|--------|-----------------------------------|
| 0    | 1      | $2^0 = 1$                       |
| 1    | 2      | $2^1 = 2$                       |
| 2    | 4      | $2^2 = 2 \times 2 = 4$          |
| 3    | 8      | $2^3 = 2 \times 2 \times 2 = 8$ |
| 4    | 16     | $2^4 = 16$                      |
| 5    | 32     | $2^5 = 32$                      |
| 6    | 64     | $2^6 = 64$                      |
| 7    | 128    | $2^7 = 128$                     |
| 8    | 256    | $2^8 = 256$                     |
| 9    | 512    | $2^9 = 512$                     |
| 10   | 1024   | $2^{10} = 1024$                 |
| 11   | 2048   | $2^{11} = 2048$                 |
| 12   | 4096   | $2^{12} = 4096$                 |
| 13   | 8192   | $2^{13} = 8192$                 |

#### Half spicy

"Half spicy" mitigates how quickly points increase with each additional faan.

It starts the same as full spicy, but from 4 faan onward, points double every two faan instead of every one. An odd-numbered faan above 4—e.g., 5 faan—is always 1.5 times the points of the previous faan.

| Faan | Points | Formula                  |
|------|--------|--------------------------|
| 0    | 1      | $2^0 = 1$              |
| 1    | 2      | $2^1 = 2$              |
| 2    | 4      | $2^2 = 4$              |
| 3    | 8      | $2^3 = 8$              |
| 4    | 16     | $2^4 = 16$             |
| 5    | 24     | $1.5 \times 2^4 = 24$  |
| 6    | 32     | $2^5 = 32$             |
| 7    | 48     | $1.5 \times 2^5 = 48$  |
| 8    | 64     | $2^6 = 64$             |
| 9    | 96     | $1.5 \times 2^6 = 96$  |
| 10   | 128    | $2^7 = 128$            |
| 11   | 192    | $1.5 \times 2^7 = 192$ |
| 12   | 256    | $2^8 = 256$            |
| 13   | 384    | $1.5 \times 2^8 = 384$ |
