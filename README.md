# PoC for targeted wireless MITM attacks with Linux

This is the accompanying source code for my blog post titled "[Targeted Man-in-the-Middle (MITM) wireless network attacks with Linux](https://shreyanshja.in/posts/2020-mitm-with-linux/)".

The code has been written for my computer. Hence, your mileage may vary. But it is small and should be easy to port to your computer.

To run it:

1. Update redacted constants in the code with correct values for case.
2. Regenerate the SSL certificates if they are expired.
3. Compile proxy.go into binary `proxy`.
4. Execute `fire.py`.
