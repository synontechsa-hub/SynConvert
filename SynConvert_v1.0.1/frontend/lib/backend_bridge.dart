import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;

/// Represents the status of the Python backend environment.
enum BackendStatus {
  ready,
  pythonMissing,
  moduleMissing,
  error,
}

/// A single file conversion proposal returned by the backend scan.
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

/// The bridge between Flutter and the Python SynConvert backend.
class BackendBridge {
  static final BackendBridge _instance = BackendBridge._internal();
  factory BackendBridge() => _instance;
  BackendBridge._internal();

  // FIX: Resolve absolute path at runtime relative to the executable location.
  // Using relative '..' paths was fragile depending on CWD at launch time.
  // Platform.resolvedExecutable gives us the actual running binary location,
  // from which we can reliably locate the .venv regardless of how the app
  // was launched (via launch.py, flutter run, or direct .exe).
  String get _backendRoot {
    final exeDir = File(Platform.resolvedExecutable).parent;
    // In debug (flutter run): exe is in build/windows/x64/runner/Debug/
    // Walk up to find the SynConvert root (where .venv lives)
    // We look for .venv up to 6 levels up
    Directory dir = exeDir;
    for (int i = 0; i < 6; i++) {
      final venv = Directory(p.join(dir.path, '.venv'));
      if (venv.existsSync()) return dir.path;
      final parent = dir.parent;
      if (parent.path == dir.path) break; // reached filesystem root
      dir = parent;
    }
    // Fallback: assume we're running from the project root
    return Directory.current.path;
  }

  String get _pythonPath {
    final root = _backendRoot;
    if (Platform.isWindows) {
      return p.join(root, '.venv', 'Scripts', 'python.exe');
    }
    // macOS / Linux
    return p.join(root, '.venv', 'bin', 'python');
  }

  /// Check if the backend is reachable and correctly configured.
  Future<BackendStatus> checkStatus() async {
    try {
      final result = await Process.run(
        _pythonPath,
        ['-m', 'backend.main', '--help'],
        workingDirectory: _backendRoot,
      );
      if (result.exitCode == 0) return BackendStatus.ready;

      if (result.stderr.toString().contains('No module named backend')) {
        return BackendStatus.moduleMissing;
      }
      return BackendStatus.error;
    } catch (e) {
      return BackendStatus.pythonMissing;
    }
  }

  /// Run a scan on the input directory and return a list of proposals.
  Future<List<ScanProposal>> scanDirectory(String inputPath) async {
    final result = await Process.run(
      _pythonPath,
      ['-m', 'backend.main', 'scan', '--input', inputPath, '--json'],
      workingDirectory: _backendRoot,
    );

    if (result.exitCode != 0) {
      throw Exception('Scan failed: ${result.stderr}');
    }

    final List<dynamic> data = jsonDecode(result.stdout as String);
    return data
        .map((item) => ScanProposal.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// Execute the conversion process for the given input/output.
  /// FIX: stdout and stderr are now merged into a single interleaved stream
  /// so FFmpeg progress (written to stderr) appears in real time alongside
  /// any stdout output — previously stderr was only yielded after stdout closed.
  Stream<String> convert({
    required String input,
    required String output,
    String? preset,
    bool review = false,
  }) async* {
    final args = [
      '-m', 'backend.main', 'convert',
      '--input', input,
      '--output', output,
    ];

    if (preset != null) args.addAll(['--preset', preset]);
    if (!review) args.add('--no-review');

    final process = await Process.start(
      _pythonPath,
      args,
      workingDirectory: _backendRoot,
    );

    // FIX: Merge stdout and stderr into one interleaved stream using
    // StreamController so both streams are consumed concurrently.
    final controller = StreamController<String>();

    // Decode both streams and add to controller
    final stdoutSub = process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    final stderrSub = process.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    // Close controller once both streams and the process are done
    Future.wait([stdoutSub.asFuture(), stderrSub.asFuture()]).then((_) async {
      final exitCode = await process.exitCode;
      if (exitCode != 0) {
        controller.add('Process exited with error code $exitCode');
      }
      await controller.close();
    });

    yield* controller.stream;
  }
}
