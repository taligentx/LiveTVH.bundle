# LiveTVH.bundle
LiveTVH provides live TV streaming for [Plex](https://plex.tv) via [Tvheadend](https://tvheadend.org), including metadata from Tvheadend's EPG, [theTVDB](https://thetvdb.com), and [The Movie DB](https://www.themoviedb.org).

## Features
* Plays all Tvheadend video channels, audio channels, and recordings, including IPTV and ATSC/DVB sources.
* Direct streaming when the codec and resolution of channels are set using Tvheadend channel tags.
* Provides the Tvheadend EPG for channels in the Plex channel description.
* Displays metadata and artwork from theTVDB (using EPG zap2it IDs if available) and The Movie DB.
* Supports Tvheadend stable versions 4.2.x and unstable development versions 4.3.x.

## Release notes
* 2018.07.25 - [LiveTVH 1.4](https://github.com/taligentx/LiveTVH.bundle/releases/tag/v1.4)
  * New: Support both plain and digest authentication for Tvheadend HTTP authentication
  * New: Channel artwork via HTTPS now falls back to SSL without authentication if necessary due to a [Plex issue](https://forums.plex.tv/t/https-broken/216635/8)
  * Changed: Plex Web no longer supports direct streaming 256kbps audio, lowered specified audio bitrate for audio direct streaming
  * Bugfix: Recordings failed to display when resolution was not set
  * Bugfix: Plugin failed to respond if theTVDB metadata is enabled and thetvdb.com is unreachable
  * Bugfix: Plugin failed to respond when accessing recordings if the Tvheadend recordings data contains invalid UTF-8 characters, added fallback to ISO-8859-1 characters

* 2018.07.08 - [LiveTVH 1.3](https://github.com/taligentx/LiveTVH.bundle/releases/tag/v1.3)
  * Changed: Tvheadend channel tags support additional codecs, resolutions, and radio (audio-only) channels
  * Changed: Changed image filenames to match Plex channel guidelines
  * Changed: Replaced deprecated string substitution per [#18](https://github.com/taligentx/LiveTVH.bundle/pull/18)

* 2017.05.22 - [LiveTVH 1.2](https://github.com/taligentx/LiveTVH.bundle/releases/tag/v1.2)
  * New: Paginated channel lists with a configurable number of items per page - this helps with longer channel lists (a necessity for IPTV providers with thousands of channels).
  * New: Tvheadend recordings for playback - located at the end of the first page of the channel list (a display bug with several Plex clients prevents placing it at the beginning of the list).
  * New: Codec identification using Tvheadend channel tags (experimental).  This can enable direct streaming for H264-AAC streams on some clients (see setup notes below).
  * Changed: EPG parser to improve support for IPTV sources, including using images for a show if specified in the EPG (if other metadata providers are not available or are missing artwork).
  * Changed: EPG item limit to 20k items/20MB (again, for IPTV sources).
  * Changed: Plex clients will now display channel thumbnails as video clip objects (widescreen thumbnails) if metadata providers are disabled.
  * Changed: Code housekeeping (partially PEP8-conformant)
  * Bugfix: transcoding quality options not visible during playback
  * Bugfix: episode names from EPG were not set on Plex for Android

* 2017.05.14 - [LiveTVH 1.1](https://github.com/taligentx/LiveTVH.bundle/releases/tag/v1.1)
  * EPG is no longer hard set - the number of EPG items requested is now based on the number of channels and hours of EPG data necessary (up to a maximum of 10,000 items or 10MB of data).
  * Bugfix: Thumbnails fallback to a channel logo when a show matches theTVDB but does not have a poster.
  * Bugfix: 12-hour time displays correctly on non-linux platforms.
  * Bugfix: Year displays for movies (when available from TMDb).

* 2017.05.10 - Initial release 1.0

## Screenshots
![Plex Web Posters Screenshot](https://cloud.githubusercontent.com/assets/12835671/26337954/21753de4-3f42-11e7-895d-005c4da6b0a5.jpg)
![Plex Web Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927053/c6212fda-35b8-11e7-98ca-ad636e62076e.jpg)
![Plex Web Recordings Screenshot](https://cloud.githubusercontent.com/assets/12835671/26337967/3b2e345c-3f42-11e7-9d58-1671841e06ab.jpg)
![Plex Home Theater Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927057/d018e2ee-35b8-11e7-9f41-27554d4fca97.jpg)
![Plex Media Player Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927122/2137e76a-35b9-11e7-85a0-949371255083.jpg)
![Plex iOS Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927072/dbecdd3c-35b8-11e7-80d9-056e59088501.jpg)

## Setup
1. [Download LiveTVH.bundle](https://github.com/taligentx/LiveTVH.bundle/releases/) and unzip to the [Plex Media Server/Plug-ins](https://support.plex.tv/hc/en-us/articles/201106098-How-do-I-find-the-Plug-Ins-folder-) directory.  Alternatively, `git clone` this repository to the Plug-ins directory to keep track of the latest changes.
2. Open the Tvheadend web interface and navigate to Configuration > Users > Passwords.  Create a user and password.
3. Navigate to Configuration > Users > Access Entries and create a new access entry for the user.
4. Select "Web interface", Streaming > "Basic", and Video recorder > "Basic".

    ![Tvheadend Access Entry screenshot](https://user-images.githubusercontent.com/12835671/42663549-95fdfd76-85fb-11e8-8b02-b2022d8c6cff.png)
5. Set the LiveTVH preferences with the Tvheadend LAN IP address/hostname (or WAN for remote access), username, and password.

   ![Prefs Screenshot](https://cloud.githubusercontent.com/assets/12835671/26337942/0a4d9724-3f42-11e7-9654-7c8e82e4877a.jpg)
6. Watch!

## Notes
* Channels will take a bit of time to load initially while metadata is fetched and speed up over time as the cache is built up and stored for 30 days.  Up to 30 channels per page works reasonably well.

* Direct streaming of channels on Plex Web, iOS, Roku, and Android requires identifying the channel's codecs and resolution using Tvheadend channel tags.  Create and set channel tags in Tvheadend as appropriate for each channel:
  * Video tags: `H264`, `MPEG2`, `HEVC`, `VP8`, `VP9`
  * Audio tags: `AAC`, `AAC-LATM`, `AC3`, `EAC3`, `MP2`, `MP3`, `VORBIS`
  * Video and audio tags may be combined into single tags: `MPEG2-AC3`, `H264-AAC`, etc.
  * Video resolution tags: `HDTV`, `720p`, `SDTV`

  ![Tvheadend Channel Tags Screenshot](https://cloud.githubusercontent.com/assets/12835671/26338051/e0cb75dc-3f42-11e7-85a0-7af80e425a21.png)

* Radio (audio-only) channels are also identified using Tvheadend channel tags - create and set a `Radio` tag in Tvheadend on the appropriate channels for audio-only playback, as well as audio tags (for example, `AAC`) for direct streaming.

* While Tvheadend recordings can be played, managing new recordings will need to be handled outside of Plex, or by using [Plex DVR](https://www.plex.tv/features/dvr) and [tvhProxy](https://github.com/jkaberg/tvhProxy)).

* Watching remotely may require Tvheadend to have a public-facing address, as some clients will attempt to directly play the Tvheadend stream instead of running through the Plex transcoder.

  In this case, putting Tvheadend behind a [reverse proxy with SSL](https://www.nginx.com/resources/admin-guide/reverse-proxy/) is highly recommended, as the Tvheadend username and password is sent using HTTP Basic Authentication and is not secure over plain HTTP.

* LiveTVH preferentially searches for metadata on theTVDB using a show's zap2it ID if provided through Tvheadend's EPG.

  For example, [zap2xml](http://zap2xml.awardspace.info) produces an XMLTV file with a zap2it ID for each show (if available) - Tvheadend includes this information in its EPG, and LiveTVH will use this ID to match the correct show. If a zap2it ID is not available, LiveTVH will fallback to searching by name.

  If searching theTVDB fails by zap2it ID but succeeds by name, LiveTVH will display the zap2it ID in the summary as an alert that the show's zap2it entry on theTVDB may be missing/incorrect - consider updating theTVDB.com with the correct information to improve search results.  For example, many shows are in the older `SHxxxxxx` format, while the current format is `EPxxxxxxxx`.

  ![zap2it Screenshot](https://cloud.githubusercontent.com/assets/12835671/25927080/e3b33ec6-35b8-11e7-8eb2-d0f0a3cfabc1.jpg)

## Known Issues
* Plex Web currently does not display a detailed pre-play page if metadata is enabled - this is a bug/side effect of setting up the channels as movies instead of video clips to display posters correctly. Channels can be played directly from the channel list.
* Plex for Xbox One fails to play channels - this may be due to a [known Plex issue](https://forums.plex.tv/discussion/173008/known-issues-in-1-8-0#latest).
* Metadata searches are not localized.
* Plex does not provide options to flag a stream as interlaced in channels - expect combing artifacts on Plex clients that do not support deinterlacing, unfortunately.  Plex's native live TV viewing works with [tvhProxy](https://github.com/jkaberg/tvhProxy) and supports deinterlacing.
