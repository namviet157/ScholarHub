import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="text-center max-w-md space-y-4">
        <h1 className="text-4xl font-bold text-foreground">404</h1>
        <p className="text-xl text-muted-foreground">This page does not exist.</p>
        <p className="text-sm text-muted break-all">{location.pathname}</p>
        <div className="flex gap-3 justify-center pt-2">
          <Button asChild variant="default">
            <Link to="/">Home</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/search">Explore papers</Link>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
