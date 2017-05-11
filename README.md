# LiveTVH.bundle
LiveTVH provides live TV streaming for [Plex](https://plex.tv) via [Tvheadend](https://tvheadend.org), including metadata from Tvheadend's EPG, [theTVDB](https://thetvdb.com), and [The Movie DB](https://www.themoviedb.org).

![Plex Web Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927053/c6212fda-35b8-11e7-98ca-ad636e62076e.jpg)
![Plex Home Theater Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927057/d018e2ee-35b8-11e7-9f41-27554d4fca97.jpg)
![Plex iOS Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927072/dbecdd3c-35b8-11e7-80d9-056e59088501.jpg)


## Setup
1. Download and unzip LiveTVH.bundle (or clone the repository) to the [Plex Media Server/Plug-ins](https://support.plex.tv/hc/en-us/articles/201106098-How-do-I-find-the-Plug-Ins-folder-) directory, and rename (if necessary) to `LiveTVH.bundle`.
2. Set the LiveTVH preferences with the Tvheadend local or remotely accessible IP address/hostname, username, and password.

   ![Prefs Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927076/df92f73c-35b8-11e7-99d2-5250e964cc04.jpg)
3. Watch!

## Notes
* LiveTVH implements channels only at this point (recordings can be handled by [Plex DVR](https://www.plex.tv/features/dvr) and [tvhProxy](https://github.com/jkaberg/tvhProxy)).

* Channels will take a bit of time to load initially while metadata is fetched and speed up over time as images and metadata requests are stored in the cache.

* Watching remotely may require Tvheadend to have a public-facing address, as some clients will attempt to directly play the Tvheadend stream instead of running through the Plex transcoder.
  
  In this case, putting Tvheadend behind a reverse proxy with SSL is highly recommended, as the Tvheadend username and password is sent using HTTP Basic Authentication and is not secure over plain HTTP.

* LiveTVH preferentially searches for metadata on theTVDB using a show's zap2it ID if provided through Tvheadend's EPG.
  
  For example, [zap2xml](http://zap2xml.awardspace.info) produces an XMLTV file with a zap2it ID for each show (if available) - Tvheadend includes this information in its EPG, and LiveTVH will use this ID to match the correct show. If a zap2it ID is not available, LiveTVH will fallback to searching by name.
  
  If searching theTVDB fails by zap2it ID but succeeds by name, LiveTVH will display the zap2it ID in the summary as an alert that the show's zap2it entry on theTVDB may be missing/incorrect - consider updating theTVDB.com with the correct information to improve search results.  For example, many shows are in the older `SHxxxxxx` format, while the current format is `EPxxxxxxxx`.
  
  ![zap2it Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927080/e3b33ec6-35b8-11e7-8eb2-d0f0a3cfabc1.jpg)

## Known Issues
* Plex Web currently does not display a detailed pre-play page - this is a bug/side effect of setting up the channels as movies instead of video clips to display posters correctly - channels can be played directly from the channel list.
* Plex for Xbox One fails to play channels - this is a [known Plex issue](https://forums.plex.tv/discussion/173008/known-issues-in-1-8-0#latest).
* Metadata searches are not localized.
* Plex does not provide options to flag a stream as interlaced - expect combing artifacts, unfortunately.
