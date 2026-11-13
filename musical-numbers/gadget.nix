{ pkgs, lib, settings, ... }:

let
  # The Pi's address on the cable to the phone. The Pi gives the phone an address from the same network.
  ip = "10.42.0.1";

  # songs/<digit>.<any format>, for example songs/1.mp3
  songNames = builtins.filter (name: builtins.match "[1-9]\\..+" name != null)
    (builtins.attrNames (if builtins.pathExists ./songs then builtins.readDir ./songs else { }));
  digits = map (name: builtins.substring 0 1 name) songNames;

  # Each song as <digit>.wav, 16 kHz mono 16-bit, like the phone call
  songs = pkgs.runCommand "musical-numbers-songs" { nativeBuildInputs = [ pkgs.ffmpeg-headless ]; } (
    "mkdir $out\n" + lib.concatMapStrings (name: ''
      ffmpeg -nostdin -loglevel error -i ${builtins.path { path = ./songs + "/${name}"; name = "song"; }} \
        -ar 16000 -ac 1 -sample_fmt s16 $out/${builtins.substring 0 1 name}.wav
    '') songNames
  );

  # The whole dialplan for the phone: only the song numbers. (FreeSWITCH's own default dialplan has demos,
  # an operator on 0 and voicemail.) A number without a song does not connect.
  dialplan = pkgs.writeText "default.xml" ''
    <include>
      <context name="default">
    ${lib.concatMapStrings (d: ''
        <extension name="mn_${d}">
          <condition field="destination_number" expression="^${d}$">
            <action application="answer"/>
            <action application="playback" data="${songs}/${d}.wav"/>
            <action application="hangup"/>
          </condition>
        </extension>
    '') digits}
      </context>
    </include>
  '';

  phoneUser = pkgs.writeText "phone.xml" ''
    <include>
      <user id="${lib.escapeXML settings.phone.user}">
        <params>
          <param name="password" value="${lib.escapeXML settings.phone.password}"/>
        </params>
        <variables>
          <variable name="user_context" value="default"/>
        </variables>
      </user>
    </include>
  '';

  # FreeSWITCH's vanilla config with the changes that the Docker version made, plus a fixed address
  # and no STUN lookup (there is no internet)
  vanilla = "${pkgs.freeswitch}/share/freeswitch/conf/vanilla";
  conf = pkgs.runCommand "musical-numbers-freeswitch-conf" { } ''
    mkdir $out
    sed -e '0,/<include>/s||<include>\n  <X-PRE-PROCESS cmd="set" data="local_ip_v4=${ip}"/>|' \
        -e 's/stun:stun.freeswitch.org/${ip}/' \
        ${vanilla}/vars.xml > $out/vars.xml
    sed -e 's/external_rtp_ip/local_ip_v4/; s/external_sip_ip/local_ip_v4/' \
        -e 's/local-network-acl" value="localnet.auto"/local-network-acl" value="musical_local"/' \
        -e 's/\(inbound-codec-prefs" value="\)[^"]*"/\1OPUS,G722,PCMU,PCMA"/' \
        -e 's/\(outbound-codec-prefs" value="\)[^"]*"/\1OPUS,G722,PCMU,PCMA"/' \
        -e 's/\(inbound-codec-negotiation" value="\)generous"/\1scrooge"/' \
        -e 's/\(apply-inbound-acl" value="\)domains"/\1musical_local"/' \
        -e 's|<param name="context" value="public"/>|<param name="context" value="default"/>|' \
        ${vanilla}/sip_profiles/internal.xml > $out/internal.xml
    sed -e '/<network-lists>/a\    <list name="musical_local" default="deny">\n      <node type="allow" cidr="10.42.0.0/24"/>\n    </list>' \
        ${vanilla}/autoload_configs/acl.conf.xml > $out/acl.conf.xml
    # Stop here if a newer FreeSWITCH changed the vanilla files
    grep -q 'local_ip_v4=${ip}' $out/vars.xml
    if grep -q 'data="external_[a-z]*_ip=stun:' $out/vars.xml; then exit 1; fi
    grep -q 'context" value="default"' $out/internal.xml
    grep -q 'apply-inbound-acl" value="musical_local"' $out/internal.xml
    grep -q 'local-network-acl" value="musical_local"' $out/internal.xml
    grep -q 'list name="musical_local"' $out/acl.conf.xml
  '';
in
{
  assertions = [
    {
      assertion = digits != [ ];
      message = "musical-numbers: put songs named 1.mp3 ... 9.mp3 (any format) in musical-numbers/songs/, and build with ./build.sh";
    }
    {
      assertion = lib.length digits == lib.length (lib.unique digits);
      message = "musical-numbers: songs/ has two files for the same digit";
    }
  ];

  services.freeswitch = {
    enable = true;
    configDir = {
      "vars.xml" = "${conf}/vars.xml";
      "sip_profiles/internal.xml" = "${conf}/internal.xml";
      "autoload_configs/acl.conf.xml" = "${conf}/acl.conf.xml";
      "dialplan/default.xml" = dialplan;
      "directory/default/phone.xml" = phoneUser;
    };
  };

  # The phone is on a cable straight to the Pi: the Pi has a fixed address and gives the phone one.
  # No router, no internet.
  networking.useNetworkd = true;
  networking.useDHCP = false;
  systemd.network.networks."10-phone" = {
    matchConfig.Type = "ether";
    address = [ "${ip}/24" ];
    networkConfig = {
      DHCPServer = true;
      ConfigureWithoutCarrier = true; # the address is there before the phone is plugged in
    };
    dhcpServerConfig = {
      PoolOffset = 100;
      PoolSize = 100;
      EmitDNS = false;
      EmitRouter = false;
    };
    linkConfig.RequiredForOnline = "no";
  };
  # FreeSWITCH can start before the address is set
  boot.kernel.sysctl."net.ipv4.ip_nonlocal_bind" = 1;
  # DHCP, SIP, and FreeSWITCH's RTP ports
  networking.firewall.allowedUDPPorts = [ 67 5060 ];
  networking.firewall.allowedUDPPortRanges = [ { from = 16384; to = 32768; } ];
}
