{ pkgs ? import <nixpkgs> {} }:

# The models of listen.py: keyword spotting for "story" in kws/, speech recognition while awake in asr/.
# Local: nix-build story/models.nix -o story/models
let
  kws = pkgs.fetchurl {
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2";
    hash = "sha256-8XABO0cW5Btiub/YCWh8IHzveY75vGU01SThevm2Vho=";
  };
  asr = pkgs.fetchurl {
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2";
    hash = "sha256-nFWSg+hJjT/pWRPHnKHLRUuyYoGsKxArQTBsfXUnZdk=";
  };
  # The recognizer's word pieces, for its hotwords: the release has no bpe.model
  asrBpe = pkgs.fetchurl {
    url = "https://huggingface.co/desh2608/icefall-asr-librispeech-pruned-transducer-stateless7-streaming-small/resolve/be162ecc09bade73063a671fad9d18220149d25b/data/lang_bpe_500/bpe.model";
    hash = "sha256-xTQz3gg8SmrRLQNFUO8i3mjOxixPWJMqe2uLLx50P6U=";
  };
in
pkgs.runCommand "story-models" { } ''
  mkdir -p $out/kws $out/asr
  tar xjf ${kws} -C $out/kws --strip-components=1 --wildcards '*/README.md' '*/tokens.txt' '*/bpe.model' '*.int8.onnx'
  tar xjf ${asr} -C $out/asr --strip-components=1 --wildcards '*/README.md' '*/tokens.txt' '*.int8.onnx'
  cp ${asrBpe} $out/asr/bpe.model
''
