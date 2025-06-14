{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.dbus
    pkgs.libGL
    pkgs.libGLU
    pkgs.xorg.libX11
    pkgs.xorg.libXext
    pkgs.xorg.libXrender
    pkgs.xorg.libXrandr
    pkgs.xorg.libXinerama
    pkgs.xorg.libXcursor
    pkgs.xorg.libXi
    pkgs.xorg.libXfixes
    pkgs.fontconfig
    pkgs.freetype
    pkgs.ffmpeg
  ];
}