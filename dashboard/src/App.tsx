import { useEffect, useState } from "react";
import { ClaimPage } from "./ClaimPage";
import { Queue } from "./Queue";

function useHash() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const update = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("hashchange", update);
    };
  }, []);
  return hash;
}

function Page({ hash }: Readonly<{ hash: string }>) {
  const claim = /^#\/claims\/([\w-]+)$/.exec(hash);
  if (claim) return <ClaimPage key={claim[1]} claimId={claim[1]} />;
  return <Queue />;
}

export function App() {
  const hash = useHash();
  return (
    <>
      <header className="masthead">
        <a className="brand" href="#/">
          UnderCover <span className="tagline">Claims</span>
        </a>
        <nav>
          <a href="#/">Queue</a>
        </nav>
      </header>
      <main>
        <Page hash={hash} />
      </main>
    </>
  );
}
