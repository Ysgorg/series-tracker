# Next episode tracker

A script that fetches information about next episodes of your favorite series from [next-episode.net](https://next-episode.net) and prints it to your terminal.

The information includes the time of the next episode,
 or whether the show has ended/cancelled or the time of the next episode is yet to be announced.

 This script piggy-backs off next-episode.net, and will stop working when next-episode.net changes their design.

## Installation

```
git clone https://github.com/Ysgorg/series-tracker.git
cd series-tracker
pip3 install -r requirements.txt
```

## Usage

Specify your favorite series in [series.txt](series.txt).
Each line must correspond to a next-episode.net link, such as in the first six lines in the example file.

Then, do `python3 path/to/series-tracker`.
