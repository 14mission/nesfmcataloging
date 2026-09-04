#!/usr/bin/env bash
echo APPLY SCRIPT TO nesfm.archive.test.tsv
./gsht2cit.py nesfm.archive.test.tsv
mv nesfm.archive.test.4cit.csv nesfm.archive.test.4cit.just_got.csv
echo LOOK FOR DIFFS BELOW
diff -bu0 nesfm.archive.test.4cit.expected.csv nesfm.archive.test.4cit.just_got.csv
echo END OF TEST SCRIPT
