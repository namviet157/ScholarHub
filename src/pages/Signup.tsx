import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";

const Signup = () => {
  const [fullname, setFullname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [university, setUniversity] = useState("");
  const [major, setMajor] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const { error } = await signUp({
      fullname: fullname.trim(),
      email: email.trim(),
      password,
      university: university.trim() || undefined,
      major: major.trim() || undefined,
    });
    setSubmitting(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success(
      "Sign up successful. If you have enabled email verification, please check your email before logging in."
    );
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      <Header showSearch={false} />
      <div className="container mx-auto px-4 py-12 flex justify-center">
        <Card className="w-full max-w-md border-border bg-card">
          <CardHeader>
            <CardTitle className="text-foreground">Sign up</CardTitle>
            <CardDescription>
              Create a Supabase Auth account; your profile will be saved in the{" "}
              <span className="font-medium">public.users</span> table after a valid login session.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullname">Full name</Label>
                <Input
                  id="fullname"
                  required
                  value={fullname}
                  onChange={(e) => setFullname(e.target.value)}
                  className="bg-accent border-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-accent border-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-accent border-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="university">University / College (optional)</Label>
                <Input
                  id="university"
                  value={university}
                  onChange={(e) => setUniversity(e.target.value)}
                  className="bg-accent border-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="major">Major (optional)</Label>
                <Input
                  id="major"
                  value={major}
                  onChange={(e) => setMajor(e.target.value)}
                  className="bg-accent border-border"
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-primary text-primary-foreground"
                disabled={submitting}
              >
                {submitting ? "Creating account…" : "Sign up"}
              </Button>
              <p className="text-sm text-muted text-center">
                Already have an account?{" "}
                <Link to="/login" className="text-primary font-medium hover:underline">
                  Log in
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Signup;
