import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { StateMessage } from "../components/StateMessage";

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <StateMessage
        icon={<Compass className="h-10 w-10" />}
        title="Page not found"
        action={<Link to="/" className="btn-primary">Go to RankEngine home</Link>}
      >
        The page you are looking for doesn’t exist.
      </StateMessage>
    </div>
  );
}
