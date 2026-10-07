#Super Mario for Econometrics



## Prototype

I want you to use python to help me develop a very simple game.

I was to use A,S,D,W to control left, down, right, up direction of a super mario (in the scene of its classical 1985 version, and use "u" to let it jump. 

Deisign a simple scene as the beginning of World 1-1. There is a "coin box" with a "?" symbol in the middle of the screen. When I move Mario beneath it and jump to hit the coin box, there will be a random variable (follow a N(0,1) normal distribution) coming out of the box. These number will be stored in a csv file.

After 10 hits, the coin box will become empty. If I walk mario to the right end of the screen, there is a gap, and Mario will die. Game is over. 

 You design the Mario scene and objects as close to the 1985 classical version. Let me know how to test and play this DIY game.



## Initial scenes

Add an initial scene to the game. User will use W and S for up and down to choose among the following scenes.

1. random outcomes.

2. binary control variable

3. multiple control variables

If the user choose Option 1, he enters the scene developed above. (Currently, you can end the game if he chooses Option 2 or 3. The corresponding scenes will be developed later.)



## Option 2

Now you develop the scene for Option 2. You only implement a small change upon the scene in Option 1. In Option 2, the coin box's color will be determined by a random binary variable draw with equal probablity with value either 0 or 1.

If the value is 1, the color of the coin box is black.

If the value is 0, the color of the coin box is white.

The binary variable is draw every 0.2 second. 

Again the coin box will be empty after 10 hits. You use a csv files to record the binary variable (0 or 1) and the outcome from N(0,1).

**A follow-up prompt**: Change the outcome data generation process. If the binary variable is 0, draw the outcome from N(0,1); if the binary variable is 1, draw the outcome from N(1,1).



## Option 3

You modify the scene in Option 2 to develop the scene in Option 3. Every 0.2 second, you draw three independent variables uniformly from integers between 0 to 255, as "R", "G", and "B" to determine the color (in terms of the RGB) of the coin box.  The outcome from the coin box is determined by the formula R + G + B + N(0,1).

Again the coin box will be empty after 10 hits. You use a csv files to record the values of "R", "G", and "B" and the outcome.



A follow-up prompt: In Option 2, remove the upper-right text "Normal" and "N(0,1)" or "N(1,1)". In Option 3, remove the upper-right text "Normal" and the corresponding "N(???, 1)".



## Option 4

You develop an Option 4, "Endogneity". The scene of Option 4 is based on Option 2.

There will be two locations for the single coin box. You draw a binary random variable "Z" with equal probability. If Z == 0, the coin box is near the vine; if Z == 1, the coin box is near the pipe. 

When Z == 1, you draw another binary variable X. X == 1 with probability 0.7, and X == 0 with probability 0.3. 

When Z == 0, you draw another binary variable X. X == 1 with probability 0.3, and X == 0 with probability 0.7.

The outcome y ~ N(2,1) if X == 1 and Z==1; y ~N(1,1) if X == 0 and Z == 1; y~N(1,1) if X = 1 and Z ==0; y ~ N(-1, 1) if X == 0 and Z == 0. 

Z is re-draw every time the block is hit. X is re-draw every 0.2 second. Save x, z, and y into a csv file.



**In econometrics**, Z plays the role of instrument and X is the endogenous varaible. The subgroup average treatment effect

$E[ \Delta | Z = 1]$ = 1 and $E[ \Delta | Z = 0] = 2$

and thus the overall $ATT = 1 * 0.5 + 2 * 0.5 = 1.5$.

However, without Z 

$E[ Y | X = 1] = 2 * 0.7 + 1 * 0.3 = 1.7$;

$E[ Y | X = 0] = 1 * 0.3 + (-1) * 0.7 = -0.4$;

$E[ Y | X = 1]  -  E[ Y | X = 0 ] = 2.1$. This is the population OLS coefficient if we naively regressionn Y on X. 

In economic applications, the most stylized example takes y as the salary, z as cognitive ability (high and low), and x as college entry.


