"""Screen Sharing — Apple Screen Sharing High Performance mode client library.

Layout (no symbols re-exported here — import directly from the modules):

    screen_sharing.cli                        main()  — the `screen-sharing` console entry point
    screen_sharing.proxy.session              Session, SessionConfig (the engine)
    screen_sharing.proxy.input                InputController
    screen_sharing.proxy.media.*              HEVC + AAC-ELD decoders, NAL utilities
    screen_sharing.proxy.protocol.*           wire protocol (auth, SRTP, RFB, etc.)
    screen_sharing.frontend.connect_prompt    launch-time terminal prompt
    screen_sharing.frontend.desktop.*         native wgpu + glfw viewer
"""
__version__ = "0.2.0"
