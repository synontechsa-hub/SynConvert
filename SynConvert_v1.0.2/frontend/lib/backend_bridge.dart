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
    // FIX: First check for SYNCONVERT_ROOT env var set by launch.py
    // This is the most reliable method since launch.py knows the exact root.
    final envRoot = Platform.environment['SYNCONVERT_ROOT'];
    if (envRoot != null && envRoot.isNotEmpty) {
      return envRoot;
    }

    // Fallback: walk up from the executable looking for .venv
    // Handles cases where the app is launched directly without launch.py
    final exeDir = File(Platform.resolvedExecutable).parent;
    Directory dir = exeDir;
    for (int i = 0; i < 6; i++) {
      final venv = Directory(p.join(dir.path, '.venv'));
      if (venv.existsSync()) return dir.path;
      final parent = dir.parent;
      if (parent.path == dir.path) break;
      dir = parent;
    }

    // Last resort: current working directory
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

  /// Returns a copy of the current environment with PYTHONIOENCODING=utf-8
  /// injected so Python subprocesses always emit UTF-8 regardless of the
  /// Windows system locale (which defaults to cp1252/cp850).
  Map<String, String> get _pythonEnv => {
        ...Platform.environment,
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONUTF8': '1', // Python 3.7+ UTF-8 mode
      };

  /// Check if the backend is reachable and correctly configured.
  Future<BackendStatus> checkStatus() async {
    try {
      final result = await Process.run(
        _pythonPath,
        ['-u', '-m', 'backend.main', '--help'],
        workingDirectory: _backendRoot,
        environment: _pythonEnv,
        stdoutEncoding: utf8,
        stderrEncoding: utf8,
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

  /// Fetch the current backend configuration.
  Future<Map<String, dynamic>> getConfig() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'config', '--get'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      throw Exception('Failed to get config: ${result.stderr}');
    }

    return jsonDecode(result.stdout as String) as Map<String, dynamic>;
  }

  /// Update the backend configuration.
  Future<void> setConfig(Map<String, dynamic> config) async {
    final configJson = jsonEncode(config);
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'config', '--set', configJson],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      throw Exception('Failed to set config: ${result.stderr}');
    }
  }

  /// Remove completed/skipped jobs from the queue.
  Future<void> clearCompletedJobs() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'queue', '--clear-done'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );
    if (result.exitCode != 0) {
      throw Exception('Failed to clear queue: ${result.stderr}');
    }
  }

  /// Reset failed jobs back to pending.
  Future<void> resetFailedJobs() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'queue', '--reset-failed'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );
    if (result.exitCode != 0) {
      throw Exception('Failed to reset queue: ${result.stderr}');
    }
  }

  /// Resume processing the current queue.
  Stream<String> resumeQueue() async* {
    final process = await Process.start(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'queue', '--resume'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );

    final controller = StreamController<String>();

    final stdoutSub = process.stdout
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    final stderrSub = process.stderr
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    Future.wait([stdoutSub.asFuture(), stderrSub.asFuture()]).then((_) async {
      await process.exitCode;
      await controller.close();
    });

    yield* controller.stream;
  }

  /// Get the current status of all jobs in the queue.
  Future<List<Map<String, dynamic>>> getQueueStatus() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'status', '--json'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      // If queue doesn't exist yet, it's not strictly an error for the UI.
      return [];
    }

    final List<dynamic> data = jsonDecode(result.stdout as String);
    return data.cast<Map<String, dynamic>>();
  }

  /// Run a scan on the input directory and return a list of proposals.
  Future<List<ScanProposal>> scanDirectory(String inputPath) async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'scan', '--input', inputPath, '--json'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
      stderrEncoding: utf8,
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
      '-u', '-m', 'backend.main', 'convert',
      '--input', input,
      '--output', output,
    ];

    if (preset != null) args.addAll(['--preset', preset]);
    if (!review) args.add('--no-review');

    final process = await Process.start(
      _pythonPath,
      args,
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );

    // FIX: Merge stdout and stderr into one interleaved stream using
    // StreamController so both streams are consumed concurrently.
    final controller = StreamController<String>();

    // Decode both streams with allowMalformed:true so a single corrupt byte
    // (e.g. from FFmpeg progress with non-UTF8 filename fragment) never crashes
    // the whole stream — it gets replaced with U+FFFD instead.
    final stdoutSub = process.stdout
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    final stderrSub = process.stderr
        .transform(Utf8Decoder(allowMalformed: true))
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
