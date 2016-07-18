This program purposed for EEG calibration, especially, for visual SSVEP uses.

Using pygame to create a flickering stimulus for EEG signal measurement,
where the flickering frequency is specified at 10Hz and 12 Hz.

10Hz just for SSVEP detection, and 12Hz for closed eye (rilex) detection.
These 2 frequencies (maybe) could increase the confidence when installing the electrode.
But,  it just happen on Occipital and Parietal area. (maybe create eye blink for Frontal Calibration)
The method is CCA (Canonical Correlation Analysis), its just based on correlation.
So when the correlation value show good behavior, it means signals could be transformed into another subspace with less noisier one
Sometimes, just need 2 worked electodes of 4, to get good correlation value. Then the other 2, in fact, bad and full of noise.
So bad..

Basically, Thats none of my bussiness. lol.  as long as its detect better eeg signal on flickering stimulation.

The program inspired from many sources, check for more detail in the source
1. Matlab
2. https://gith~~ub.com/mahdan~~ahmad/py-emo~~kit
3. cours~~era : https://gith~~ub.com/MT~~G/sm~~s-too~~ls
