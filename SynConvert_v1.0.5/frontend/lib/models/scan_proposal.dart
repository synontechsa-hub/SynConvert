class ScanProposal {
  final String source;
  final String relative;
  final String outputFilename;
  final int season;
  final int episode;
  final String title;

  ScanProposal({
    required this.source,
    required this.relative,
    required this.outputFilename,
    required this.season,
    required this.episode,
    required this.title,
  });

  factory ScanProposal.fromJson(Map<String, dynamic> json) {
    return ScanProposal(
      source: json['source'] as String,
      relative: json['relative'] as String,
      outputFilename: json['output_filename'] as String,
      season: json['season'] as int,
      episode: json['episode'] as int,
      title: json['title'] as String,
    );
  }
}
