import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import { 
    ThemeProvider, 
    createTheme, 
    CssBaseline, 
    Container, 
    TextField, 
    Button, 
    LinearProgress, 
    Typography, 
    Box,
    Slider,
    Alert,
    Snackbar
} from '@mui/material';

const theme = createTheme();

function App() {
    const [formData, setFormData] = useState({
        prompt: '',
        negative_prompt: '',
        steps: 28,
        guidance_scale: 7.0,
        strength: 0.8
    });
    const [initImage, setInitImage] = useState(null);
    const [progress, setProgress] = useState(0);
    const [generatedImage, setGeneratedImage] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState(null);

    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSliderChange = (name) => (event, newValue) => {
        setFormData({ ...formData, [name]: newValue });
    };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setInitImage(reader.result.split(',')[1]);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setIsGenerating(true);
        setProgress(0);
        setGeneratedImage(null);
        setError(null);

        const requestData = {
            ...formData,
            init_image: initImage
        };

        try {
            const response = await fetch('http://localhost:5000/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'An error occurred');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const decodedChunk = decoder.decode(value, { stream: true });
                const lines = decodedChunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data:')) {
                        const data = JSON.parse(line.slice(5));
                        if (data.progress) {
                            setProgress(data.progress);
                        } else if (data.image_path) {
                            setGeneratedImage(`http://192.168.56.1:5000/${data.image_path}`);
                            setIsGenerating(false);
                        } else if (data.error) {
                            throw new Error(data.error);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error.message);
            setError(error.message);
            setIsGenerating(false);
        }
    };

    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <Container maxWidth="sm">
                <Typography variant="h4" component="h1" gutterBottom>
                    Stable Diffusion Image Generator
                </Typography>
                <form onSubmit={handleSubmit}>
                    <TextField
                        fullWidth
                        margin="normal"
                        label="Prompt"
                        name="prompt"
                        value={formData.prompt}
                        onChange={handleInputChange}
                        required
                    />
                    <TextField
                        fullWidth
                        margin="normal"
                        label="Negative Prompt"
                        name="negative_prompt"
                        value={formData.negative_prompt}
                        onChange={handleInputChange}
                    />
                    <Typography gutterBottom>Steps: {formData.steps}</Typography>
                    <Slider
                        value={formData.steps}
                        onChange={handleSliderChange('steps')}
                        min={1}
                        max={100}
                        step={1}
                        valueLabelDisplay="auto"
                    />
                    <Typography gutterBottom>Guidance Scale: {formData.guidance_scale}</Typography>
                    <Slider
                        value={formData.guidance_scale}
                        onChange={handleSliderChange('guidance_scale')}
                        min={1}
                        max={20}
                        step={0.1}
                        valueLabelDisplay="auto"
                    />
                    <Typography gutterBottom>Strength: {formData.strength}</Typography>
                    <Slider
                        value={formData.strength}
                        onChange={handleSliderChange('strength')}
                        min={0}
                        max={1}
                        step={0.01}
                        valueLabelDisplay="auto"
                    />
                    <input
                        type="file"
                        accept="image/*"
                        onChange={handleFileChange}
                        style={{ margin: '20px 0' }}
                    />
                    <Button 
                        variant="contained" 
                        color="primary" 
                        type="submit" 
                        fullWidth
                        disabled={isGenerating}
                    >
                        {isGenerating ? 'Generating...' : 'Generate Image'}
                    </Button>
                </form>
                {isGenerating && (
                    <Box sx={{ width: '100%', mt: 2 }}>
                        <LinearProgress variant="determinate" value={progress} />
                    </Box>
                )}
                {generatedImage && (
                    <Box sx={{ mt: 2 }}>
                        <img 
                            src={generatedImage} 
                            alt="Generated" 
                            style={{ width: '100%', marginTop: 20 }}
                        />
                    </Box>
                )}
                <Snackbar open={!!error} autoHideDuration={6000} onClose={() => setError(null)}>
                    <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
                        {error}
                    </Alert>
                </Snackbar>
            </Container>
        </ThemeProvider>
    );
}

ReactDOM.render(<App />, document.getElementById('root'));
