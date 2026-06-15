from genacademy_coach.eval_split import write_manifest
from genacademy_coach.settings import CoachSettings


def main() -> None:
    settings = CoachSettings.from_env()
    manifest = write_manifest(
        settings.eval_questions_dir,
        settings.eval_manifest_path,
        seed="genacademy-coach-v1",
    )
    print(f"wrote {settings.eval_manifest_path} with {len(manifest['items'])} private-source items")


if __name__ == "__main__":
    main()
